"""Publish and collect bounded synthetic results through public GitHub repositories."""

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError
from urllib.request import Request, build_opener

from beacon_runner import HERE, REPO, TASK, NoRedirect, available, parse, read_json, verify

API = "https://api.github.com"
REGISTRY_URL = f"https://raw.githubusercontent.com/{REPO}/main/autonomous/mailboxes.json"
RESULT_PATH = f"beacon-results/{TASK}.json"
CONSENT_PATH = "beacon-registration.json"
ISSUES_URL = f"{API}/repos/{REPO}/issues"
ISSUE_INDEX = f"{ISSUES_URL}?state=open&sort=updated&direction=desc&per_page=20"
RECEIPTS = HERE / "receipts" / TASK
REPO_NAME = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9-]{0,38}/[a-zA-Z0-9_.-]{1,100}")
ISSUE_TITLE = "Beacon mailbox: "
MAILBOX_ERRORS = (OSError, ValueError, RecursionError)


class ReadBudgetExhausted(Exception):
    pass


def bounded_reads(api):
    remaining = 48

    def get(url, **kwargs):
        nonlocal remaining
        if remaining == 0:
            raise ReadBudgetExhausted
        remaining -= 1
        try:
            return api(url, **kwargs)
        except HTTPError as error:
            if error.code in {403, 429}:
                raise ReadBudgetExhausted from error
            raise

    return get


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


def read_blob(source, path):
    if (type(source) is not dict or source.get("type") != "file"
            or source.get("path") != path or source.get("encoding") != "base64"
            or type(source.get("size")) is not int or not 0 < source["size"] <= 1024
            or type(source.get("content")) is not str
            or not re.fullmatch(r"[0-9a-f]{40}", str(source.get("sha")))):
        raise ValueError("Invalid mailbox response")
    raw = base64.b64decode(source["content"].replace("\n", ""), validate=True)
    blob = f"blob {len(raw)}\0".encode() + raw
    if len(raw) != source["size"] or hashlib.sha1(blob).hexdigest() != source["sha"]:
        raise ValueError("Invalid mailbox size or blob identity")
    return raw


def issue_candidate(issue):
    if (type(issue) is not dict or issue.get("state") != "open" or "pull_request" in issue
            or type(issue.get("number")) is not int or not 0 < issue["number"] < 2**31
            or type(issue.get("title")) is not str or not issue["title"].startswith(ISSUE_TITLE)
            or type(issue.get("user")) is not dict):
        raise ValueError("Expected an open Beacon mailbox issue")
    name = issue["title"][len(ISSUE_TITLE):]
    user = issue["user"]
    if (not REPO_NAME.fullmatch(name) or name.lower() == REPO.lower()
            or name.split("/")[1] in {".", ".."}
            or user.get("type") != "User" or type(user.get("id")) is not int
            or user["id"] < 1 or type(user.get("login")) is not str
            or name.split("/")[0].lower() != user["login"].lower()):
        raise ValueError("Expected an owner-authored issue for a personal mailbox")
    return name.lower(), user["id"], issue["number"]


def issue_enrollment(candidate, api):
    name, owner_id, number = candidate
    repo_url = f"{API}/repos/{name}"
    repo = api(repo_url)
    if (type(repo) is not dict or type(repo.get("id")) is not int or repo["id"] < 1
            or type(repo.get("owner")) is not dict or repo["owner"].get("id") != owner_id
            or repo["owner"].get("type") != "User" or repo.get("private") is not False
            or repo.get("visibility") != "public" or repo.get("archived") is not False
            or type(repo.get("full_name")) is not str or repo["full_name"].lower() != name):
        raise ValueError("Mailbox ownership or visibility could not be verified")
    entry = {"repository": name, "repository_id": repo["id"], "owner_id": owner_id}
    proof = api(f"{repo_url}/contents/{CONSENT_PATH}", limit=4096)
    expected = {"schema_version": 1, "beacon": REPO, "issue": number,
                "repository_id": entry["repository_id"], "task_id": TASK, "consent": True}
    actual = parse(read_blob(proof, CONSENT_PATH), 1024)
    if (type(actual) is not dict or actual != expected
            or any(type(actual[key]) is not type(value) for key, value in expected.items())):
        raise ValueError("Missing exact, task-specific mailbox consent")
    return entry


def current_candidate(number, api):
    if type(number) is not int or not 0 < number < 2**31:
        raise ValueError("Expected a positive GitHub mailbox issue number")
    candidate = issue_candidate(api(f"{ISSUES_URL}/{number}", limit=131072))
    if candidate[2] != number:
        raise ValueError("Mailbox issue number changed")
    return candidate


def publish(result, config, *, api=request):
    repo = config["mailbox_repository"]
    if type(repo) is not str or not REPO_NAME.fullmatch(repo):
        raise ValueError("Expected a GitHub owner/repository for mailbox publication")
    entries = enrollment(api(REGISTRY_URL))
    entry = next((item for item in entries if item["repository"].lower() == repo.lower()), None)
    if "mailbox_issue" in config:
        candidate = current_candidate(config["mailbox_issue"], api)
        if candidate[0] != repo.lower():
            raise ValueError("Mailbox issue names another repository")
        entry = issue_enrollment(candidate, api)
        if any(item["owner_id"] == entry["owner_id"]
               or item["repository_id"] == entry["repository_id"]
               or item["repository"].lower() == entry["repository"].lower()
               for item in entries):
            raise ValueError("Mailbox conflicts with a manual enrollment")
    elif entry is None:
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


def collect(registry, feed, receipts=RECEIPTS, *, api=request, self_service=False):
    entries = enrollment(registry)
    if not available(feed):
        return
    for entry in entries:
        collect_entry(entry, feed, receipts, api)
    if not self_service:
        return
    try:
        issues = api(ISSUE_INDEX, limit=2097152)
        if type(issues) is not list or len(issues) > 20:
            raise ValueError("Invalid issue index")
    except MAILBOX_ERRORS as error:
        print(f"Mailbox issue index skipped ({type(error).__name__})", file=sys.stderr)
        return
    manual_ids = {entry["repository_id"] for entry in entries}
    manual_names = {entry["repository"].lower() for entry in entries}
    seen_owners = {entry["owner_id"] for entry in entries}
    candidates = 0
    for issue in issues:
        try:
            candidate = issue_candidate(issue)
        except ValueError:
            continue
        name, owner_id, number = candidate
        if (name in manual_names or owner_id in seen_owners
                or (receipts / f"{owner_id}.json").exists()):
            continue
        if candidates == 6:
            break
        candidates += 1
        seen_owners.add(owner_id)
        try:
            entry = issue_enrollment(candidate, api)
        except MAILBOX_ERRORS as error:
            status = error.code if isinstance(error, HTTPError) else type(error).__name__
            print(f"Mailbox registration {number} skipped ({status})", file=sys.stderr)
            continue
        if entry["repository_id"] not in manual_ids:
            collect_entry(entry, feed, receipts, api, candidate=candidate)


def collect_entry(entry, feed, receipts, api, *, candidate=None):
    path = receipts / f"{entry['owner_id']}.json"
    if path.exists():
        return
    try:
        url = f"{API}/repos/{entry['repository']}/contents/{RESULT_PATH}"
        if candidate is None:
            mailbox_url(entry, api)
        source = api(url, limit=4096)
        raw = read_blob(source, RESULT_PATH)
        receipt = verify(parse(raw, 1024), feed)
        if candidate is None:
            # Recheck identity after resolving the mutable repository name.
            mailbox_url(entry, api)
        else:
            number = candidate[2]
            if current_candidate(number, api) != candidate or issue_enrollment(candidate, api) != entry:
                raise ValueError("Mailbox enrollment changed")
            receipt["registration_issue"] = number
    except MAILBOX_ERRORS as error:
        status = error.code if isinstance(error, HTTPError) else type(error).__name__
        print(f"Mailbox {entry['repository_id']} skipped ({status})", file=sys.stderr)
        return
    receipt.update(entry, source_blob_sha=source["sha"], source_sha256=hashlib.sha256(raw).hexdigest())
    receipts.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as output:
        output.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(f"Verified mailbox {entry['repository_id']}")


if __name__ == "__main__":
    try:
        collect(read_json(HERE / "mailboxes.json"), read_json(HERE / "feed.json"),
                api=bounded_reads(request), self_service=True)
    except ReadBudgetExhausted:
        print("Anonymous GitHub read budget exhausted; collection deferred", file=sys.stderr)
