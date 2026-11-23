"""Read-only BTC/USDC market observation, Python 3.11+."""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.request import HTTPRedirectHandler, Request, build_opener

TASK = "btc-usdc-top-of-book-v1"
FEEDS = {
    "coinbase": "https://api.exchange.coinbase.com/products/BTC-USD/book?level=1",
    "kraken": "https://api.kraken.com/0/public/Depth?pair=XBTUSDC&count=1",
}
BUDGET = Decimal("173")
FRICTION = Decimal("0.0125")  # 100 bps fee + 25 bps buffer per side
POLL_SECONDS = 3600


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def book(venue, payload):
    if venue == "kraken":
        if payload["error"] or len(payload["result"]) != 1:
            raise ValueError("Kraken returned an error or an ambiguous market")
        payload = next(iter(payload["result"].values()))
    bid, ask = (tuple(Decimal(str(x)) for x in payload[side][0][:2])
                for side in ("bids", "asks"))
    if any(not x.is_finite() or not Decimal("0.00000001") <= x <= 10**9
           for x in (*bid, *ask)) or bid[0] > ask[0]:
        raise ValueError("Invalid order book")
    return {"bid": bid, "ask": ask}


def estimate(buy, sell):
    ask, available_to_buy = buy["ask"]
    bid, available_to_sell = sell["bid"]
    unit_cost = ask * (1 + FRICTION)
    quantity = BUDGET / unit_cost
    if min(available_to_buy, available_to_sell) < quantity:
        return {"status": "insufficient_top_depth"}
    net = quantity * (bid * (1 - FRICTION) - unit_cost)
    return {"status": "candidate" if net >= Decimal("0.50") else "below_threshold",
            "estimated_net_usdc": str(net.quantize(Decimal("0.0001")))}


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def observe():
    start = time.monotonic()
    opener = build_opener(NoRedirect)
    books = {}
    timestamps = {}
    for venue, url in FEEDS.items():
        request = Request(url, headers={"User-Agent": "Mehecske-Market-Pilot/1"})
        with opener.open(request, timeout=5) as response:
            data = response.read(65537)
        timestamps[venue] = utc_now()
        if len(data) > 65536:
            raise ValueError("Oversized response")
        books[venue] = book(venue, json.loads(data))
    if time.monotonic() - start > 5:
        raise ValueError("Quote collection exceeded five seconds")
    routes = {f"{buy}_to_{sell}": estimate(books[buy], books[sell])
              for buy, sell in (("coinbase", "kraken"), ("kraken", "coinbase"))}
    return {"task_id": TASK, "sources": FEEDS, "received_at_utc": timestamps,
            "quotes": books, "routes": routes}


def authorized(path, now):
    try:
        config = json.loads(path.read_text(encoding="utf-8-sig"))
        starts = config["starts_unix"]
        return (config["enabled"] is True and config["task_id"] == TASK
                and type(starts) is int and starts <= now < starts + 7 * 86400)
    except (OSError, ValueError, TypeError, KeyError):
        return False


def run(path, once):
    if not authorized(path, time.time()):
        print("Disabled, invalid or expired operator opt-in.", file=sys.stderr)
        return 2
    while authorized(path, time.time()):
        started = time.monotonic()
        event = {"task_id": TASK, "attempted_at_utc": utc_now()}
        try:
            result = subprocess.run(
                [sys.executable, "-B", str(Path(__file__).resolve()), str(path.resolve()), "--worker"],
                capture_output=True, timeout=30, encoding="utf-8", check=True,
            )
            event.update(json.loads(result.stdout))
        except (subprocess.SubprocessError, ValueError):
            event["error"] = "market_data_unavailable"
        event["duration_seconds"] = round(time.monotonic() - started, 3)
        print(json.dumps(event, default=str), flush=True)
        if once:
            return 1 if "error" in event else 0
        deadline = started + POLL_SECONDS
        while authorized(path, time.time()) and time.monotonic() < deadline:
            time.sleep(min(5, max(0, deadline - time.monotonic())))
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        if not authorized(args.config, time.time()):
            return 2
        try:
            print(json.dumps(observe(), default=str))
        except (OSError, ValueError, KeyError, IndexError, TypeError, InvalidOperation):
            return 1
        return 0
    return run(args.config, args.once)


if __name__ == "__main__":
    sys.exit(main())
