"""Interactive, one-shot client. Prompts for credentials without echo."""
import argparse
import getpass
import json
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPRedirectHandler, ProxyHandler, Request, build_opener,
)

from beacon import CATALOG, CONSENT, new_secret


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("action", choices=[
        "new-secret", "register", "feed", "verify-and-receive", "unsubscribe",
        "publish", "revoke",
    ])
    args = parser.parse_args()
    action = args.action
    if action == "new-secret":
        print(new_secret())
        return 0

    headers = {}
    body = {}
    if action == "register":
        print("Receive later synthetic research notices when you query the feed.")
        print("You can unsubscribe at any time. No project executes on receipt.")
        if input("Type YES to consent: ") != "YES":
            return 1
        body = {"consent": CONSENT, "future_notices": True}
    else:
        headers["Authorization"] = "Bearer " + getpass.getpass("Bearer secret: ")

    if action == "publish":
        print("Synthetic projects: " + ", ".join(CATALOG))
        body = {"project": input("Project: "), "ttl_seconds": int(input("TTL seconds: "))}
    if action == "revoke":
        body = {"call_id": input("Call ID: ")}
    if action == "verify-and-receive":
        body = {"invitation": json.loads(input("Paste one invitation as single-line JSON: "))}

    data = None
    if action != "feed":
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    request = Request(f"http://127.0.0.1:{args.port}/{action}", data=data, headers=headers)
    opener = build_opener(ProxyHandler({}), NoRedirect())
    try:
        with opener.open(request, timeout=5) as response:
            print(response.read().decode())
        return 0
    except HTTPError as error:
        print(error.read().decode())
    except URLError:
        print("Beacon connection failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
