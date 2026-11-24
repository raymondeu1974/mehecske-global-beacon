"""Check the public checkout and both built distributions without printing payloads."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import subprocess
import tarfile
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "public-export.json"
RECEIPT = re.compile(r"autonomous/receipts/synthetic-shortest-path-v1/([1-9][0-9]{0,19})\.json")
SECRET = re.compile(
    rb"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----"
    rb"|\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}"
    rb"|(?:AKIA|ASIA)[A-Z0-9]{16}|xox[baprs]-[A-Za-z0-9-]{15,}"
    rb"|sk-(?:proj-|ant-)?[A-Za-z0-9_-]{24,}|pypi-[A-Za-z0-9_-]{30,})\b"
    rb"|(?im:^[ \t]*(?:password|api_key|client_secret|access_token)[ \t]*[:=][ \t]*"
    rb"[\"'][A-Za-z0-9+/=_-]{16,}[\"'])"
)
MAX_FILE_BYTES = 1_000_000


def require(condition, message):
    if not condition:
        raise ValueError(message)


def normalized(data):
    return data.replace(b"\r\n", b"\n")


def checked_data(data, label):
    require(len(data) <= MAX_FILE_BYTES and b"\x00" not in data, f"Non-text or oversized file: {label}")
    try:
        data.decode("utf-8")
    except UnicodeError:
        raise ValueError(f"Non-UTF-8 file: {label}") from None
    require(not SECRET.search(data), f"Potential credential in {label}")
    return normalized(data)


def tracked_files():
    index = subprocess.check_output(["git", "ls-files", "--stage", "-z"], cwd=ROOT)
    for entry in index.decode("utf-8").split("\0"):
        if not entry:
            continue
        metadata, path = entry.split("\t", 1)
        mode, object_id, stage = metadata.split()
        require(mode in {"100644", "100755"} and stage == "0", "Non-regular or unmerged Git entry")
        size = subprocess.check_output(["git", "cat-file", "-s", object_id], cwd=ROOT)
        require(int(size) <= MAX_FILE_BYTES, "Oversized staged Git blob")
        yield path, subprocess.check_output(["git", "cat-file", "blob", object_id], cwd=ROOT)


def check_receipt(owner, data):
    try:
        receipt = json.loads(data)
        required = {"owner_id", "repository", "repository_id", "reproduced", "result",
                    "schema_version", "source_blob_sha", "source_sha256"}
        require(isinstance(receipt, dict) and set(receipt) in (required, required | {"registration_issue"}),
                "Invalid receipt fields")
        for key in ("owner_id", "repository_id", "registration_issue", "schema_version"):
            if key in receipt:
                require(type(receipt[key]) is int and 0 < receipt[key] < 10**20, "Invalid receipt number")
        require(str(receipt["owner_id"]) == owner and receipt["schema_version"] == 1
                and receipt["reproduced"] is True, "Invalid receipt identity")
        require(re.fullmatch(r"[A-Za-z0-9-]{1,39}/[A-Za-z0-9_.-]{1,100}", receipt["repository"]),
                "Invalid public repository name")
        for key, length in (("source_blob_sha", 40), ("source_sha256", 64)):
            require(re.fullmatch("[0-9a-f]{%d}" % length, receipt[key]), "Invalid receipt digest")
        result = receipt["result"]
        require(type(result) is dict and set(result) == {"distance", "shortest_paths", "task_id"}
                and type(result["distance"]) is int and type(result["shortest_paths"]) is int
                and result == {"distance": 4, "shortest_paths": 4, "task_id": "synthetic-shortest-path-v1"},
                "Invalid public benchmark result")
        canonical = json.dumps(receipt, indent=2, sort_keys=True).encode() + b"\n"
        require(data == canonical, "Noncanonical receipt")
    except (TypeError, ValueError, RecursionError):
        raise ValueError("Invalid generated public mailbox receipt") from None


def check_tree(policy, staged):
    files = {}
    reviewed = policy["checkout"]
    seen = set()
    manifest_seen = False
    for path, raw in staged.items():
        if path == MANIFEST:
            manifest_seen = True
        elif match := RECEIPT.fullmatch(path):
            check_receipt(match[1], checked_data(raw, "public receipt"))
        else:
            require(path in reviewed, "Unreviewed tracked file. Review the local diff and public inventory.")
            data = checked_data(raw, path)
            require(hashlib.sha256(data).hexdigest() == reviewed[path], f"Unreviewed file content: {path}")
            seen.add(path)
        files[path] = checked_data(raw, MANIFEST) if path == MANIFEST else raw
    require(manifest_seen and seen == set(reviewed), "Public inventory differs from checkout")
    return files


def check_archive(entries, mapping, generated, files):
    seen = set()
    for name, read in entries:
        require(name not in seen and (name in mapping or name in generated),
                "Unexpected or duplicate distribution member")
        seen.add(name)
        data = checked_data(read(), "distribution member")
        if name in mapping:
            require(data == normalized(files[mapping[name]]), f"Distribution content mismatch: {name}")
    require(seen == set(mapping) | generated, "Distribution is missing approved members")


def check_dist(directory, policy, files):
    project = tomllib.loads(files["pyproject.toml"].decode())["project"]
    stem = project["name"].replace("-", "_") + "-" + project["version"]
    wheel = directory / f"{stem}-py3-none-any.whl"
    sdist = directory / f"{stem}.tar.gz"
    require(set(directory.iterdir()) == {wheel, sdist}, "Expected exactly the reviewed wheel and sdist")
    require(not wheel.is_symlink() and not sdist.is_symlink(), "Distribution archive must be a regular file")

    with zipfile.ZipFile(wheel) as archive:
        def wheel_entries():
            for member in archive.infolist():
                mode = stat.S_IFMT(member.external_attr >> 16)
                require(not member.is_dir() and mode in (0, stat.S_IFREG)
                        and member.file_size <= MAX_FILE_BYTES, "Invalid wheel member")
                yield member.filename, lambda: archive.read(member)
        metadata = {f"{stem}.dist-info/{name}" for name in ("METADATA", "WHEEL", "entry_points.txt", "RECORD")}
        check_archive(wheel_entries(), policy["wheel"], metadata, files)

    with tarfile.open(sdist, "r:gz") as archive:
        def sdist_entries():
            for member in archive:
                require(member.isfile() and member.size <= MAX_FILE_BYTES, "Invalid sdist member")
                yield member.name, lambda: archive.extractfile(member).read()
        mapping = {f"{stem}/{path}": path for path in policy["sdist"]}
        check_archive(sdist_entries(), mapping, {f"{stem}/PKG-INFO"}, files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, help="directory containing only the wheel and sdist")
    args = parser.parse_args()
    try:
        require(subprocess.run(["git", "diff", "--quiet", "--"], cwd=ROOT).returncode == 0,
                "Stage intended changes before checking the checkout")
        staged = dict(tracked_files())
        policy = json.loads(checked_data(staged[MANIFEST], MANIFEST))
        files = check_tree(policy, staged)
        if args.dist is not None:
            check_dist(args.dist, policy, files)
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, subprocess.CalledProcessError, tarfile.TarError, zipfile.BadZipFile) as exc:
        # Exception strings from libraries can include input bytes or filenames.
        parser.exit(1, f"Public export rejected: {exc if type(exc) is ValueError else type(exc).__name__}\n")
    print(f"Public export passed ({len(files)} tracked files"
          f"{', wheel and sdist' if args.dist is not None else ''}).")


if __name__ == "__main__":
    main()
