"""Publish and collect bounded synthetic results through public GitHub repositories."""

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from beacon_runner import HERE, REPO, TASK, NoRedirect, available, parse, read_json, verify

API = "https://api.github.com"
REGISTRY_URL = f"https://raw.githubusercontent.com/{REPO}/main/autonomous/mailboxes.json"
RESULT_PATH = f"beacon-results/{TASK}.json"
RECEIPTS = HERE / "receipts" / TASK
REPO_NAME = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9-]{0,38}/[a-zA-Z0-9_.-]{1,100}")


def request(url, *, payload=None, token=None, limit=16384):
    headers = {"Accept": "application/vnd.github+json", "Cache-Control": "no-cache"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    req = Request(url, data, headers, method="PUT" if data is not None else "GET")
    with build_opener(NoRedirect).open(req, timeout=10) as response:
        return parse(response.read(limit + 1), limit)


def enrollment(registry):
    if (type(registry) is not dict or type(registry.get("schema_version")) is not int
            or registry["schema_version"] != 1 or type(registry.get("mailboxes")) is not list
            or len(registry["mailboxes"]) > 20):
        raise ValueError("Invalid mailbox registry")
    names, ids, owners = set(), set(), set()
    for entry in registry["mailboxes"]:
        if (type(entry) is not dict or entry.keys() != {"repository", "repository_id", "owner_id"}
                or type(entry["repository"]) is not str
                or not REPO_NAME.fullmatch(entry["repository"])
                or entry["repository"].lower() == REPO.lower()
                or any(part in {".", ".."} for part in entry["repository"].split("/"))
                or any(type(entry[key]) is not int or entry[key] < 1
                       for key in ("repository_id", "owner_id"))):
            raise ValueError("Invalid mailbox entry")
        name, repo_id, owner_id = entry["repository"].lower(), entry["repository_id"], entry["owner_id"]
        if name in names or repo_id in ids or owner_id in owners:
            raise ValueError("Duplicate mailbox enrollment")
        names.add(name)
        ids.add(repo_id)
        owners.add(owner_id)
    return registry["mailboxes"]


def mailbox_url(entry, get):
    url = f"{API}/repos/{entry['repository']}"
    repo = get(url)
    if (type(repo) is not dict or type(repo.get("owner")) is not dict
            or repo.get("id") != entry["repository_id"] or repo["owner"].get("id") != entry["owner_id"]
            or type(repo.get("full_name")) is not str or repo["full_name"].lower() != entry["repository"].lower()
            or repo.get("visibility") != "public" or repo.get("private") is not False):
        raise ValueError("Mailbox identity or visibility changed")
    return f"{url}/contents/{RESULT_PATH}"


def publish(result, config, *, api=request):
    repo = config["mailbox_repository"]
    if type(repo) is not str or not REPO_NAME.fullmatch(repo):
        raise ValueError("Expected a GitHub owner/repository for mailbox publication")
    entries = enrollment(api(REGISTRY_URL))
    entry = next((item for item in entries if item["repository"].lower() == repo.lower()), None)
    if entry is None:
        raise ValueError("Mailbox is not enrolled")
    url = mailbox_url(entry, api)
    token = os.environ.get("BEACON_MAILBOX_TOKEN")
    if not token:
        raise ValueError("BEACON_MAILBOX_TOKEN is required for mailbox publication")
    encoded = json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    api(url, token=token, payload={
        "message": f"Publish Beacon result for {TASK}",
        "content": base64.b64encode(encoded).decode("ascii"),
    })
    return f"https://github.com/{entry['repository']}/blob/HEAD/{RESULT_PATH}"


def collect(registry, feed, receipts=RECEIPTS, *, api=request):
    entries = enrollment(registry)
    if not available(feed):
        return
    for entry in entries:
        path = receipts / f"{entry['owner_id']}.json"
        if path.exists():
            continue
        try:
            url = mailbox_url(entry, api)
            source = api(url, limit=4096)
            if (not isinstance(source, dict) or source.get("type") != "file"
                    or source.get("path") != RESULT_PATH or source.get("encoding") != "base64"
                    or type(source.get("size")) is not int or not 0 < source["size"] <= 1024
                    or type(source.get("content")) is not str
                    or not re.fullmatch(r"[0-9a-f]{40}", str(source.get("sha")))):
                raise ValueError("Invalid mailbox response")
            raw = base64.b64decode(source["content"].replace("\n", ""), validate=True)
            blob = f"blob {len(raw)}\0".encode() + raw
            if len(raw) != source["size"] or hashlib.sha1(blob).hexdigest() != source["sha"]:
                raise ValueError("Invalid mailbox size or blob identity")
            receipt = verify(parse(raw, 1024), feed)
            # Recheck identity after resolving the mutable repository name.
            mailbox_url(entry, api)
        except (OSError, URLError, ValueError, RecursionError) as error:
            status = error.code if isinstance(error, HTTPError) else type(error).__name__
            print(f"Mailbox {entry['repository_id']} skipped ({status})", file=sys.stderr)
            continue
        receipt.update(entry, source_blob_sha=source["sha"], source_sha256=hashlib.sha256(raw).hexdigest())
        receipts.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8", newline="\n") as output:
            output.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        print(f"Verified mailbox {entry['repository_id']}")


if __name__ == "__main__":
    collect(read_json(HERE / "mailboxes.json"), read_json(HERE / "feed.json"))
