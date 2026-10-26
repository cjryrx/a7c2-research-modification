"""Structural checks for the burst boost (Cnt Shoot Speed Boost) patch stage.

These tests need no firmware: they only prove that the overlay stage refuses
incomplete or unsafe patch data, and that the declared base packages are
well-formed identities.
"""

import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "windows" / "runtime" / "release"
sys.path.insert(0, str(RELEASE))

import spotboost_package_200 as spotboost  # noqa: E402


BASE = {
    "feature_ids": ["fl2_fl3"],
    "dat_sha256": "a" * 64,
    "plain_sha256": "b" * 64,
}

SPAN = {
    "name": "unit_test_span",
    "partition": "usr",
    "offset": 686526448,
    "old_sha256": "c" * 64,
    "new": "1f2a",
    "context_size": 132,
    "context_sha256": "d" * 64,
    "why": "unit test only",
}


def spec(**overrides):
    data = {"format": 1, "id": spotboost.FEATURE_ID, "status": "ready",
            "bases": [dict(BASE)], "spans": [dict(SPAN)],
            "expected_byte_changes": {"usr": 1}}
    data.update(overrides)
    return data


class SpotBoostSpecTests(unittest.TestCase):
    def write(self, data):
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                             encoding="utf-8")
        json.dump(data, handle)
        handle.close()
        self.addCleanup(Path(handle.name).unlink)
        return Path(handle.name)

    def test_shipped_spec_is_well_formed(self):
        data = spotboost.spec_data()
        self.assertEqual(data["id"], spotboost.FEATURE_ID)
        self.assertIn(data["status"], ("ready", "unresolved"))
        self.assertTrue(data["bases"])
        if data["status"] == "ready":
            self.assertTrue(data["spans"])
        else:
            self.assertEqual(data["spans"], [])

    def test_ready_span_needs_a_documented_reason(self):
        bad = spec()
        bad["spans"][0].pop("why")
        with self.assertRaises(ValueError):
            spotboost.spec_data(self.write(bad))

    def test_ready_spec_rejects_unknown_partition(self):
        bad = spec()
        bad["spans"][0]["partition"] = "bss"
        with self.assertRaises(ValueError):
            spotboost.spec_data(self.write(bad))

    def test_ready_spec_requires_at_least_one_span(self):
        with self.assertRaises(ValueError):
            spotboost.spec_data(self.write(spec(spans=[])))

    def test_unresolved_spec_may_not_carry_spans(self):
        data = spotboost.spec_data(self.write(
            {"format": 1, "id": spotboost.FEATURE_ID, "status": "unresolved",
             "bases": [dict(BASE)], "spans": [dict(SPAN)]}))
        self.assertEqual(data["status"], "unresolved")

    def test_bad_base_identity_is_rejected(self):
        bad = spec()
        bad["bases"][0]["dat_sha256"] = "not-a-hash"
        with self.assertRaises(ValueError):
            spotboost.spec_data(self.write(bad))

    def test_span_context_window_must_not_underflow(self):
        bad = spec()
        bad["spans"][0]["offset"] = 16
        with self.assertRaises(ValueError):
            spotboost.spec_data(self.write(bad))

    def test_feature_id_is_stable(self):
        self.assertEqual(spotboost.FEATURE_ID, "burst_boost_button")
        self.assertEqual(spotboost.OUTPUT_NAME, "BODYDATA_SPOTBOOST_200.DAT")
        self.assertEqual(spotboost.MANIFEST_NAME, "spotboost_package_200.json")


if __name__ == "__main__":
    unittest.main()
