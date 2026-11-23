import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ParticipationTests(unittest.TestCase):
    def test_invitation_matches_discovery_and_public_task(self):
        manifest = json.loads((ROOT / "agent-discovery.json").read_text(encoding="utf-8"))
        invitation = json.loads((ROOT / "docs/participate.json").read_text(encoding="utf-8"))
        landing = (ROOT / "docs/index.html").read_text(encoding="utf-8")
        self.assertTrue(manifest["discovery"]["invitation_url"].endswith("/docs/participate.json"))
        self.assertIn('href="participate.json"', landing)
        self.assertIn(invitation["guide_url"], landing)
        self.assertEqual(invitation["catalog_url"], manifest["discovery"]["catalog_url"])
        self.assertEqual(invitation["task_id"], "synthetic-shortest-path-v1")
        self.assertTrue(invitation["synthetic_data"])
        consent = invitation["participation"]
        self.assertTrue(consent["voluntary"])
        self.assertTrue(consent["prior_task_specific_operator_approval_required"])
        self.assertTrue(consent["separate_approval_to_publish_required"])
        self.assertFalse(consent["offline_run_requires_registration"])

    def test_baseline_and_inactive_rewards(self):
        invitation = json.loads((ROOT / "docs/participate.json").read_text(encoding="utf-8"))
        baseline = invitation["baseline"]
        for field in ("active_verified_independent_opt_ins", "verified_independent_reproductions",
                      "paid_advertising_eur"):
            self.assertEqual(baseline[field], 0, field)
        self.assertEqual(set(baseline["excluded_maintainer_account_ids"]), {66376031, 360193814})
        self.assertIsNone(baseline["visitor_count"])
        self.assertIsNone(baseline["reproduction_conversion"])
        rewards = invitation["rewards"]
        self.assertEqual(rewards["status"], "inactive")
        self.assertEqual(rewards["available_eur"], 0)
        self.assertEqual(rewards["payouts_eur"], 0)
        self.assertFalse(rewards["payment_promised"])
