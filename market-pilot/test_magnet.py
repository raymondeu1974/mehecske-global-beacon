import contextlib
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import magnet


def book(bid, ask, size="2"):
    return magnet.book("coinbase", {"bids": [[bid, size]], "asks": [[ask, size]]})


class PilotTests(unittest.TestCase):
    def test_costs_and_direction(self):
        buy, sell = book("99", "100"), book("105", "106")
        self.assertEqual(magnet.estimate(buy, sell),
                         {"status": "candidate", "estimated_net_usdc": "4.1648"})
        self.assertEqual(magnet.estimate(sell, buy)["status"], "below_threshold")
        self.assertEqual(magnet.estimate(buy, book("101", "102"))["status"],
                         "below_threshold")

    def test_depth_and_bad_quotes(self):
        self.assertEqual(magnet.estimate(book("99", "100", "0.1"), book("105", "106")),
                         {"status": "insufficient_top_depth"})
        for bid, ask in (("NaN", "100"), ("0", "100"), ("101", "100")):
            with self.assertRaises(ValueError):
                book(bid, ask)
        with self.assertRaises(ValueError):
            magnet.book("kraken", {"error": ["EQuery:Unknown asset pair"]})

    def test_kraken_format(self):
        data = {"error": [], "result": {"XBTUSDC": {
            "bids": [["99", "2", 123]], "asks": [["100", "2", 123]]}}}
        self.assertEqual(magnet.book("kraken", data), book("99", "100"))

    def test_observe_fetches_only_the_two_public_books(self):
        fixture = {"bids": [["99", "2"]], "asks": [["100", "2"]]}
        with patch("magnet.build_opener") as opener:
            reader = opener.return_value.open
            reader.return_value.__enter__.return_value.read.side_effect = [
                json.dumps(fixture).encode(),
                json.dumps({"error": [], "result": {"XBTUSDC": fixture}}).encode(),
            ]
            result = magnet.observe()
        self.assertEqual([(call.args[0].get_method(), call.args[0].full_url)
                          for call in reader.call_args_list],
                         [("GET", url) for url in magnet.FEEDS.values()])
        self.assertEqual(len(result["routes"]), 2)

    def test_consent_scope_and_expiry(self):
        path = Path("opt.json")
        with patch.object(Path, "read_text", side_effect=FileNotFoundError):
            self.assertFalse(magnet.authorized(path, 100))
        with patch.object(Path, "read_text") as read:
            config = {"enabled": True, "task_id": magnet.TASK, "starts_unix": 100}
            read.return_value = json.dumps(config)
            self.assertFalse(magnet.authorized(path, 99))
            self.assertTrue(magnet.authorized(path, 100))
            self.assertFalse(magnet.authorized(path, 100 + 7 * 86400))
            for edit in ({"enabled": False}, {"task_id": "other"}, {"starts_unix": True}):
                read.return_value = json.dumps(config | edit)
                self.assertFalse(magnet.authorized(path, 100))

    def test_disabled_never_launches_worker(self):
        with patch("magnet.subprocess.run") as worker, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(magnet.run(Path("missing-opt-in.json"), True), 2)
            worker.assert_not_called()

    def test_worker_timeout_is_reported(self):
        with (patch("magnet.authorized", return_value=True),
              patch("magnet.subprocess.run", side_effect=magnet.subprocess.TimeoutExpired("worker", 30)) as worker,
              contextlib.redirect_stdout(io.StringIO()) as output):
            self.assertEqual(magnet.run(Path("opt.json"), True), 1)
            self.assertEqual(worker.call_args.kwargs["timeout"], 30)
            self.assertEqual(json.loads(output.getvalue())["error"], "market_data_unavailable")


if __name__ == "__main__":
    unittest.main()
