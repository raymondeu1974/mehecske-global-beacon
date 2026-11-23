"""Poll the Beacon and solve a preauthorized synthetic task."""
import argparse
import hashlib
from importlib.util import module_from_spec, spec_from_file_location
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = "raymondeu1974/mehecske-global-beacon"
FEED_URL = f"https://raw.githubusercontent.com/{REPO}/main/autonomous/feed.json"
DISPATCH_URL = f"https://api.github.com/repos/{REPO}/actions/workflows/beacon-result.yml/dispatches"
TASK = "synthetic-shortest-path-v1"
DIGEST = "7fd8d4dc9a85e27c19a4d47cd3cbbd20f85261c695b5809439a2182798549f3f"
MIN_POLL = 900


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def unique_object(pairs):
    obj = dict(pairs)
    if len(obj) != len(pairs):
        raise ValueError("Duplicate JSON key")
    return obj


def parse(raw, limit):
    if len(raw) > limit:
        raise ValueError("JSON exceeds size limit")
    return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_object)


def read_json(path, limit=16384):
    with path.open("rb") as source:
        return parse(source.read(limit + 1), limit)


def public_feed():
    request = Request(FEED_URL, headers={"Cache-Control": "no-cache"})
    with build_opener(NoRedirect).open(request, timeout=15) as response:
        return parse(response.read(16385), 16384)


def available(feed):
    if (type(feed) is not dict or type(feed.get("schema_version")) is not int
            or feed["schema_version"] != 1 or type(feed.get("tasks")) is not list):
        raise ValueError("Unsupported task feed")
    matches = [t for t in feed["tasks"] if isinstance(t, dict) and t.get("id") == TASK]
    return matches == [{
        "id": TASK,
        "status": "available",
        "kind": "directed-unit-graph",
        "fixture_sha256": DIGEST,
    }]


def fixture():
    graph = read_json(ROOT / "mission-pilot" / "call.json")["fixture"]
    encoded = json.dumps(graph, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(encoded).hexdigest() != DIGEST:
        raise ValueError("Local fixture digest mismatch")
    return graph


def solve(graph):
    # Enumerate simple paths on the small pinned graph. The verifier uses BFS.
    def lengths(path):
        if path[-1] == graph["target"]:
            yield len(path) - 1
            return
        for start, end in graph["edges"]:
            if start == path[-1] and end not in path:
                yield from lengths((*path, end))

    distances = list(lengths((graph["source"],)))
    shortest = min(distances)
    return {"task_id": TASK, "distance": shortest, "shortest_paths": distances.count(shortest)}


def verify(result, feed):
    if not available(feed):
        raise ValueError("Task unavailable")
    if (type(result) is not dict or result.keys() != {"task_id", "distance", "shortest_paths"}
            or result["task_id"] != TASK
            or type(result["distance"]) is not int or type(result["shortest_paths"]) is not int):
        raise ValueError("Invalid result fields")
    spec = spec_from_file_location("pilot_verify", ROOT / "mission-pilot" / "verify.py")
    verifier = module_from_spec(spec)
    spec.loader.exec_module(verifier)
    if (result["distance"], result["shortest_paths"]) != verifier.reproduce(fixture()):
        raise ValueError("Result mismatch")
    return {"schema_version": 1, "reproduced": True, "result": result}


def dispatch(result):
    token = os.environ.get("BEACON_GITHUB_TOKEN")
    if not token:
        raise ValueError("BEACON_GITHUB_TOKEN is required for submission")
    payload = {"ref": "main", "inputs": {"result": json.dumps(result)}}
    request = Request(DISPATCH_URL, json.dumps(payload).encode(), headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2026-03-10",
        "Content-Type": "application/json",
    })
    with build_opener(NoRedirect).open(request, timeout=15) as response:
        details = parse(response.read(4097), 4096)
        run_id = details.get("workflow_run_id")
        if type(run_id) is not int or run_id < 1:
            raise ValueError("GitHub did not return a workflow run ID")
        return f"https://github.com/{REPO}/actions/runs/{run_id}"


def configuration(path):
    config = read_json(path)
    if (type(config) is not dict or config.get("enabled") is not True
            or config.get("allowed_tasks") != [TASK]
            or type(config.get("poll_seconds")) is not int
            or config["poll_seconds"] < MIN_POLL
            or type(config.get("submit")) is not bool):
        raise ValueError("Enabled operator configuration with the exact task allowlist is required")
    return config


def poll_once(config_path, state, fetch, submit):
    config = configuration(config_path)
    feed = fetch()
    if not available(feed):
        return "task unavailable"
    result = solve(fixture())
    if not config["submit"]:
        return json.dumps(verify(result, feed))
    if not available(fetch()) or not configuration(config_path)["submit"]:
        return "task unavailable before submission"
    # Reserve before POST. A timeout may mean GitHub accepted the request.
    try:
        reservation = state.open("x", encoding="utf-8")
    except FileExistsError:
        return "submission already attempted"
    with reservation:
        print("pending", file=reservation, flush=True)
    run = submit(result)
    state.write_text(f"{run}\n", encoding="utf-8")
    return f"Submission queued. Verification receipt: {run}"


def demo():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        config = root / "opt-in.json"
        state = root / "submission.txt"
        config.write_text(json.dumps({
            "enabled": True, "allowed_tasks": [TASK], "poll_seconds": MIN_POLL, "submit": True,
        }), encoding="utf-8")
        feed = read_json(HERE / "feed.json")
        receipt = root / "receipt.json"

        def submit(result):
            receipt.write_text(json.dumps(verify(result, feed)), encoding="utf-8")
            return "local receipt.json"

        for _ in range(2):
            print(poll_once(config, state, lambda: feed, submit))
        print(receipt.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    modes.add_parser("demo")
    modes.add_parser("verify")
    poll = modes.add_parser("poll")
    poll.add_argument("config", type=Path)
    poll.add_argument("--once", action="store_true")
    args = parser.parse_args()
    try:
        if args.mode == "demo":
            demo()
        elif args.mode == "verify":
            result = parse(sys.stdin.buffer.read(1025), 1024)
            print(json.dumps(verify(result, read_json(HERE / "feed.json"))))
        else:
            state = args.config.with_suffix(args.config.suffix + f".{TASK}.attempt")
            while True:
                interval = configuration(args.config)["poll_seconds"]
                print(poll_once(args.config, state, public_feed, dispatch), flush=True)
                if args.once:
                    break
                time.sleep(interval)
    except (OSError, URLError, ValueError, RecursionError) as error:
        parser.exit(2, f"Beacon stopped: {error}\n")


if __name__ == "__main__":
    main()
