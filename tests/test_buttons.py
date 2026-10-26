"""Offline tests for the slot table, value encoding and receipt files.

No camera, no pyusb, no libusb: everything here is pure Python.
Run with ``py -m unittest discover -s tests -v`` from the repository root.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bind_button import buttons  # noqa: E402
from bind_button.buttons import (  # noqa: E402
    GROUP,
    KNOWN_FUNCTIONS,
    LIST_FIRST,
    LIST_LAST,
    RECEIPT_SCHEMA,
    SLOT_BYTES,
    SLOT_COUNT,
    SLOT_FIRST,
    SLOT_LAST,
    ReceiptError,
    build_receipt,
    build_snapshot,
    decode_function_id,
    describe_slot,
    diff_snapshots,
    empty_slot,
    encode_function_id,
    function_for,
    in_list_range,
    in_slot_run,
    load_receipt,
    load_snapshot,
    receipt_after,
    receipt_before,
    receipt_filename,
    receipt_index,
    receipt_key,
    save_receipt,
    save_snapshot,
    slot_key,
)


class SlotTableTests(unittest.TestCase):
    def test_slot_run_is_the_documented_window(self):
        self.assertEqual(SLOT_FIRST, 0x0404)
        self.assertEqual(SLOT_LAST, 0x041F)
        self.assertEqual(SLOT_COUNT, 28)
        self.assertEqual(SLOT_LAST - SLOT_FIRST + 1, SLOT_COUNT)
        self.assertEqual(SLOT_BYTES, 4)

    def test_list_window_contains_the_slot_run(self):
        self.assertLess(LIST_FIRST, SLOT_FIRST)
        self.assertGreater(LIST_LAST, SLOT_LAST)
        self.assertEqual(LIST_FIRST, 0x0400)
        self.assertEqual(LIST_LAST, 0x0430)

    def test_verified_slots(self):
        self.assertEqual(buttons.VERIFIED_SLOTS[0x041B], "AF-ON")
        self.assertEqual(buttons.VERIFIED_SLOTS[0x041C], "MOVIE")
        for index in buttons.VERIFIED_SLOTS:
            self.assertTrue(in_slot_run(index))

    def test_slot_key_uses_group_0x02cf(self):
        self.assertEqual(GROUP, 0x02CF)
        self.assertEqual(slot_key(0x041B), 0x02CF041B)
        self.assertEqual(slot_key(0x0404), 0x02CF0404)
        self.assertEqual(slot_key(0x041F), 0x02CF041F)

    def test_in_slot_run_boundaries(self):
        self.assertFalse(in_slot_run(SLOT_FIRST - 1))
        self.assertTrue(in_slot_run(SLOT_FIRST))
        self.assertTrue(in_slot_run(SLOT_LAST))
        self.assertFalse(in_slot_run(SLOT_LAST + 1))

    def test_in_list_range_boundaries(self):
        self.assertFalse(in_list_range(LIST_FIRST - 1))
        self.assertTrue(in_list_range(LIST_FIRST))
        self.assertTrue(in_list_range(LIST_LAST))
        self.assertFalse(in_list_range(LIST_LAST + 1))

    def test_describe_slot_marks_verified_and_plain_slots(self):
        self.assertIn("AF-ON", describe_slot(0x041B))
        self.assertIn("verified", describe_slot(0x041B))
        self.assertEqual(describe_slot(0x0410), "custom-key slot")
        self.assertEqual(describe_slot(0x0400), "")

    def test_empty_slot(self):
        self.assertTrue(empty_slot(b"\x00\x00\x00\x00"))
        self.assertFalse(empty_slot(b"\x22\x01\x00\x00"))
        self.assertFalse(empty_slot(b""))


class FunctionTableTests(unittest.TestCase):
    def test_known_ids_and_names(self):
        self.assertEqual(KNOWN_FUNCTIONS[0x122].name, "Focus Mode")
        self.assertEqual(KNOWN_FUNCTIONS[0x300].name, "APS-C/Full-frame select")
        self.assertEqual(KNOWN_FUNCTIONS[0x305].name, "Toggle Silent Mode")
        self.assertEqual(KNOWN_FUNCTIONS[0x9C3].name, "Tracking On + Center Area AF")

    def test_function_for_unknown_id_is_none(self):
        self.assertIsNone(function_for(0x1234))
        self.assertIsNone(function_for(0x0))
        self.assertEqual(function_for(0x305).id_text, "0x00000305")

    def test_burst_boost_id_is_not_invented(self):
        # The one thing this project must not guess.  If a future change adds the
        # id, this test should be replaced by a test that pins the measured value
        # together with the hardware evidence for it.
        for entry in KNOWN_FUNCTIONS.values():
            self.assertNotIn("boost", (entry.name + " " + entry.note).lower())
            self.assertNotIn("提速", entry.name_zh)
        self.assertIn("not known", buttons.UNKNOWN_FUNCTION)

    def test_chinese_names_are_present(self):
        for entry in KNOWN_FUNCTIONS.values():
            self.assertTrue(entry.name_zh)


class EncodingTests(unittest.TestCase):
    def test_encode_matches_the_bytes_seen_in_the_dump(self):
        # Observed raw slot bytes on ILCE-7CM2 hardware.
        self.assertEqual(encode_function_id(0x122).hex(), "22010000")
        self.assertEqual(encode_function_id(0x300).hex(), "00030000")
        self.assertEqual(encode_function_id(0x305).hex(), "05030000")
        self.assertEqual(encode_function_id(0x9C3).hex(), "c3090000")

    def test_encode_decode_roundtrip(self):
        for value in (0x0, 0x1, 0xFF, 0x122, 0x300, 0x35C, 0x9C3, 0xFFFFFFFF):
            self.assertEqual(decode_function_id(encode_function_id(value)), value)

    def test_encode_rejects_out_of_range(self):
        for value in (-1, 0x100000000):
            with self.assertRaises(ValueError):
                encode_function_id(value)

    def test_encode_rejects_non_int(self):
        for value in ("0x300", 3.0, None, True):
            with self.assertRaises(TypeError):
                encode_function_id(value)

    def test_decode_requires_four_bytes(self):
        for data in (b"", b"\x00", b"\x00\x03\x00", b"\x00\x03\x00\x00\x00"):
            with self.assertRaises(Exception):
                decode_function_id(data)


class _TempDirCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


class ReceiptTests(_TempDirCase):
    def _record(self):
        return build_receipt(
            "bind", 0x041B, b"\x22\x01\x00\x00", b"\x05\x03\x00\x00",
            note="unit test",
        )

    def test_build_receipt_shape(self):
        record = self._record()
        self.assertEqual(record["schema"], RECEIPT_SCHEMA)
        self.assertEqual(record["kind"], "bind")
        self.assertEqual(record["property"]["index"], "0x041B")
        self.assertEqual(record["property"]["key"], "0x02CF041B")
        self.assertEqual(record["before"]["hex"], "22010000")
        self.assertEqual(record["before"]["compact_id"], "0x00000122")
        self.assertEqual(record["before"]["function"], "Focus Mode")
        self.assertEqual(record["after"]["compact_id"], "0x00000305")
        self.assertEqual(record["after"]["known_id"], True)
        self.assertFalse(record["forced"])
        self.assertIn("tool", record)

    def test_unknown_function_is_not_flagged_as_known(self):
        record = build_receipt("bind", 0x041B, b"\x22\x01\x00\x00", b"\x34\x12\x00\x00")
        self.assertEqual(record["after"]["compact_id"], "0x00001234")
        self.assertIsNone(record["after"]["function"])
        self.assertFalse(record["after"]["known_id"])

    def test_build_receipt_rejects_unknown_kind(self):
        with self.assertRaises(ValueError):
            build_receipt("delete", 0x041B, b"\x00" * 4, b"\x00" * 4)

    def test_save_and_load_roundtrip(self):
        record = self._record()
        path = save_receipt(self.dir, record)
        self.assertTrue(path.is_file())
        loaded = load_receipt(path)
        self.assertEqual(loaded, record)
        self.assertEqual(receipt_index(loaded), 0x041B)
        self.assertEqual(receipt_key(loaded), 0x02CF041B)
        self.assertEqual(receipt_before(loaded), b"\x22\x01\x00\x00")
        self.assertEqual(receipt_after(loaded), b"\x05\x03\x00\x00")

    def test_receipt_is_readable_json_with_chinese_names(self):
        record = build_receipt("bind", 0x041C, b"\x00\x03\x00\x00", b"\x05\x03\x00\x00")
        path = save_receipt(self.dir, record)
        raw = path.read_text(encoding="utf-8")
        self.assertIn("Toggle Silent Mode", raw)
        self.assertEqual(json.loads(raw)["kind"], "bind")

    def test_collision_does_not_overwrite_an_earlier_backup(self):
        record = self._record()
        name = "bind-0x041b-fixed.json"
        first = save_receipt(self.dir, record, filename=name)
        second = save_receipt(self.dir, record, filename=name)
        self.assertNotEqual(first, second)
        self.assertTrue(first.is_file() and second.is_file())
        self.assertEqual(second.name, "bind-0x041b-fixed-1.json")

    def test_overwrite_reuses_the_same_path(self):
        record = self._record()
        name = "bind-0x041b-fixed.json"
        first = save_receipt(self.dir, record, filename=name)
        record["readback"] = {"after_write": "05030000", "after_save": "05030000"}
        second = save_receipt(self.dir, record, filename=name, overwrite=True)
        self.assertEqual(first, second)
        self.assertEqual(load_receipt(second)["readback"]["after_save"], "05030000")

    def test_filename_format(self):
        name = receipt_filename("bind", 0x041B, when="2026-10-26T13:15:00Z")
        self.assertEqual(name, "bind-0x041b-20261026T131500Z.json")

    def test_load_rejects_wrong_schema(self):
        record = self._record()
        record["schema"] = "something-else/1"
        path = save_receipt(self.dir, record)
        with self.assertRaises(ReceiptError):
            load_receipt(path)

    def test_load_rejects_inconsistent_key(self):
        record = self._record()
        record["property"]["key"] = "0x02CF041C"
        path = save_receipt(self.dir, record)
        with self.assertRaises(ReceiptError):
            load_receipt(path)

    def test_load_rejects_bad_hex(self):
        for bad in ("zz", "123", "", "0x22"):
            record = self._record()
            record["before"]["hex"] = bad
            path = save_receipt(self.dir, record, filename="bad.json", overwrite=True)
            with self.assertRaises(ReceiptError, msg=bad):
                load_receipt(path)

    def test_load_rejects_missing_before(self):
        record = self._record()
        del record["before"]
        path = save_receipt(self.dir, record)
        with self.assertRaises(ReceiptError):
            load_receipt(path)

    def test_load_rejects_non_json(self):
        path = self.dir / "broken.json"
        path.write_text("{not json", encoding="utf-8")
        with self.assertRaises(ReceiptError):
            load_receipt(path)

    def test_load_rejects_missing_file(self):
        with self.assertRaises(ReceiptError):
            load_receipt(self.dir / "does-not-exist.json")

    def test_load_rejects_out_of_range_index(self):
        record = self._record()
        record["property"]["index"] = "0x0999"
        record["property"]["key"] = "0x02CF0999"
        path = save_receipt(self.dir, record)
        with self.assertRaises(ReceiptError):
            load_receipt(path)


class SnapshotTests(_TempDirCase):
    def test_build_and_roundtrip(self):
        values = {0x0400: b"\x01", 0x041B: b"\x22\x01\x00\x00", 0x0403: b""}
        errors = {0x0401: "PropertyError: boom"}
        record = build_snapshot(values, errors)
        path = save_snapshot(self.dir / "snap.json", record)
        loaded_values, loaded_errors, loaded_record = load_snapshot(path)
        self.assertEqual(loaded_values, values)
        self.assertEqual(loaded_errors, errors)
        self.assertEqual(loaded_record["schema"], buttons.SNAPSHOT_SCHEMA)

    def test_diff_snapshots(self):
        before = {0x041B: b"\x22\x01\x00\x00", 0x041C: b"\x00\x03\x00\x00"}
        after = {0x041B: b"\x22\x01\x00\x00", 0x041C: b"\x05\x03\x00\x00"}
        self.assertEqual(
            diff_snapshots(before, after),
            [(0x041C, b"\x00\x03\x00\x00", b"\x05\x03\x00\x00")],
        )
        self.assertEqual(diff_snapshots(before, before), [])

    def test_load_snapshot_rejects_other_schema(self):
        path = self.dir / "snap.json"
        path.write_text(json.dumps({"schema": "bind_button.receipt/1"}), encoding="utf-8")
        with self.assertRaises(ReceiptError):
            load_snapshot(path)


if __name__ == "__main__":
    unittest.main()
