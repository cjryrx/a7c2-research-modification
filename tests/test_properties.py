"""Offline tests for the property codec and the pre-write guards.

The transport is a dict-backed fake, so these tests run on any machine and can
assert exactly what would have gone to the camera -- including that nothing is
sent when a guard refuses.

The last test class runs the real CLI over the same fake transport, which covers
the receipt-before-write ordering and the save/readback sequence without a
camera.
"""

import io
import json
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bind_button import cli  # noqa: E402
from bind_button.properties import (  # noqa: E402
    GROUP,
    MAX_WRITE_BYTES,
    PropertyError,
    PropertyGuardError,
    PropertyLengthError,
    Properties,
    check_write,
    decode_u32le,
    encode_u32le,
    format_index,
    format_key,
    format_value,
    property_key,
    split_key,
)


class FakeTransport:
    """Records every call and serves values from a dict."""

    def __init__(self, values=None, fail_read=None, fail_write=None, fail_save=None):
        self.values = dict(values or {})
        self.calls = []
        self.reads = 0
        self.fail_read = fail_read
        self.fail_write = fail_write
        self.fail_save = fail_save

    def read_backup(self, key):
        self.calls.append(("read", key))
        self.reads += 1
        if self.fail_read is not None:
            raise self.fail_read
        if key not in self.values:
            return b""
        return self.values[key]

    def write_backup(self, key, data):
        self.calls.append(("write", key, bytes(data)))
        if self.fail_write is not None:
            raise self.fail_write
        self.values[key] = bytes(data)

    def save_backup(self, group):
        self.calls.append(("save", group))
        if self.fail_save is not None:
            raise self.fail_save

    def writes(self):
        return [call for call in self.calls if call[0] == "write"]

    def saves(self):
        return [call for call in self.calls if call[0] == "save"]


class KeyCodecTests(unittest.TestCase):
    def test_property_key_layout(self):
        self.assertEqual(property_key(0x041B), 0x02CF041B)
        self.assertEqual(property_key(0x041B, 0x02CF), 0x02CF041B)
        self.assertEqual(property_key(0x0000), 0x02CF0000)
        self.assertEqual(property_key(0xFFFF), 0x02CFFFFF)

    def test_property_key_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            property_key(-1)
        with self.assertRaises(ValueError):
            property_key(0x10000)
        with self.assertRaises(TypeError):
            property_key("0x041B")

    def test_split_and_format(self):
        self.assertEqual(split_key(0x02CF041B), (0x02CF, 0x041B))
        self.assertEqual(format_key(0x02CF041B), "0x02CF041B")
        self.assertEqual(format_index(0x041B), "0x041B")
        self.assertEqual(format_index(0x0004), "0x0004")

    def test_split_key_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            split_key(0x100000000)
        with self.assertRaises(ValueError):
            split_key(-1)


class ValueCodecTests(unittest.TestCase):
    def test_u32le(self):
        self.assertEqual(encode_u32le(0x305).hex(), "05030000")
        self.assertEqual(decode_u32le(bytes.fromhex("05030000")), 0x305)
        self.assertEqual(decode_u32le(b"\x00\x00\x00\x00"), 0)

    def test_u32le_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            encode_u32le(1 << 32)
        with self.assertRaises(PropertyLengthError):
            decode_u32le(b"\x01\x02\x03")

    def test_format_value(self):
        self.assertEqual(format_value(b""), "<empty>")
        self.assertEqual(format_value(None), "<none>")
        self.assertEqual(format_value(b"\x05\x03"), "0503 (2 bytes)")
        self.assertEqual(format_value(b"\x0a"), "0a (1 byte)")


class GuardTests(unittest.TestCase):
    def test_accepts_same_length(self):
        check_write(b"\x22\x01\x00\x00", b"\x05\x03\x00\x00")

    def test_refuses_length_change(self):
        with self.assertRaises(PropertyLengthError):
            check_write(b"\x22\x01\x00\x00", b"\x05\x03\x00")
        with self.assertRaises(PropertyLengthError):
            check_write(b"\x0a", b"\x0a\x00")

    def test_refuses_empty_new_value(self):
        with self.assertRaises(PropertyGuardError):
            check_write(b"\x22\x01\x00\x00", b"")

    def test_refuses_absent_property(self):
        with self.assertRaises(PropertyGuardError):
            check_write(b"", b"\x05\x03\x00\x00")

    def test_refuses_oversized_value(self):
        with self.assertRaises(PropertyGuardError):
            check_write(b"\x00" * (MAX_WRITE_BYTES + 1), b"\x00" * (MAX_WRITE_BYTES + 1))


class PropertiesReadTests(unittest.TestCase):
    def test_read_returns_bytes(self):
        transport = FakeTransport({0x02CF041B: b"\x22\x01\x00\x00"})
        self.assertEqual(Properties(transport).read(0x02CF041B), b"\x22\x01\x00\x00")
        self.assertEqual(transport.reads, 1)

    def test_read_normalises_bytearray(self):
        transport = FakeTransport({0x02CF041B: bytearray(b"\x01\x02\x03\x04")})
        self.assertEqual(Properties(transport).read(0x02CF041B), b"\x01\x02\x03\x04")

    def test_read_index(self):
        transport = FakeTransport({0x02CF041B: b"\x22\x01\x00\x00"})
        self.assertEqual(Properties(transport).read_index(0x041B), b"\x22\x01\x00\x00")

    def test_read_wraps_transport_errors_with_the_key(self):
        transport = FakeTransport(fail_read=RuntimeError("senser error 3"))
        with self.assertRaises(PropertyError) as ctx:
            Properties(transport).read(0x02CF041B)
        self.assertIn("0x02CF041B", str(ctx.exception))
        self.assertIn("senser error 3", str(ctx.exception))

    def test_read_many_keeps_per_key_failures(self):
        transport = FakeTransport({0x02CF041B: b"\x22\x01\x00\x00"})
        rows = Properties(transport).read_many([0x02CF041B, 0x02CF041C, 0x02CF041D])
        self.assertEqual(rows[0][1], b"\x22\x01\x00\x00")
        self.assertIsNone(rows[0][2])
        # An absent property reads back as zero bytes, which is a value, not an
        # error; the CLI renders it as <empty>.
        self.assertEqual(rows[1][1], b"")
        self.assertIsNone(rows[1][2])

    def test_read_many_reports_transport_failures(self):
        transport = FakeTransport(fail_read=RuntimeError("no reply"))
        rows = Properties(transport).read_many([0x02CF041B])
        self.assertIsNone(rows[0][1])
        self.assertIsInstance(rows[0][2], PropertyError)


class PropertiesWriteTests(unittest.TestCase):
    def _properties(self, values=None):
        transport = FakeTransport(values or {0x02CF041B: b"\x22\x01\x00\x00"})
        return Properties(transport), transport

    def test_write_success(self):
        properties, transport = self._properties()
        outcome = properties.write(0x02CF041B, b"\x05\x03\x00\x00")
        self.assertTrue(outcome.changed)
        self.assertEqual(outcome.before, b"\x22\x01\x00\x00")
        self.assertEqual(outcome.after, b"\x05\x03\x00\x00")
        self.assertEqual(transport.writes(), [("write", 0x02CF041B, b"\x05\x03\x00\x00")])
        self.assertEqual(transport.values[0x02CF041B], b"\x05\x03\x00\x00")

    def test_write_same_value_sends_nothing(self):
        properties, transport = self._properties()
        outcome = properties.write(0x02CF041B, b"\x22\x01\x00\x00")
        self.assertFalse(outcome.changed)
        self.assertEqual(transport.writes(), [])

    def test_write_refuses_length_change_and_sends_nothing(self):
        properties, transport = self._properties()
        with self.assertRaises(PropertyLengthError):
            properties.write(0x02CF041B, b"\x05\x03")
        self.assertEqual(transport.writes(), [])

    def test_write_refuses_absent_property_and_sends_nothing(self):
        properties, transport = self._properties({})
        with self.assertRaises(PropertyGuardError):
            properties.write(0x02CF041C, b"\x05\x03\x00\x00")
        self.assertEqual(transport.writes(), [])

    def test_write_refuses_empty_value(self):
        properties, transport = self._properties()
        with self.assertRaises(PropertyGuardError):
            properties.write(0x02CF041B, b"")
        self.assertEqual(transport.writes(), [])

    def test_write_refuses_oversized_value_before_reading(self):
        properties, transport = self._properties()
        with self.assertRaises(PropertyGuardError):
            properties.write(0x02CF041B, b"\x00" * (MAX_WRITE_BYTES + 1))
        self.assertEqual(transport.writes(), [])
        self.assertEqual(transport.reads, 0)

    def test_explicit_current_avoids_a_redundant_read(self):
        properties, transport = self._properties()
        properties.write(0x02CF041B, b"\x05\x03\x00\x00", current=b"\x22\x01\x00\x00")
        self.assertEqual(transport.reads, 0)

    def test_write_wraps_transport_errors(self):
        transport = FakeTransport({0x02CF041B: b"\x22\x01\x00\x00"},
                                  fail_write=RuntimeError("bulk write timed out"))
        with self.assertRaises(PropertyError) as ctx:
            Properties(transport).write(0x02CF041B, b"\x05\x03\x00\x00")
        self.assertIn("0x02CF041B", str(ctx.exception))
        self.assertIn("timed out", str(ctx.exception))

    def test_write_rejects_non_bytes(self):
        properties, _transport = self._properties()
        with self.assertRaises(PropertyError):
            properties.write(0x02CF041B, "05030000")


class PropertiesVerifyAndSaveTests(unittest.TestCase):
    def test_verify_accepts_matching_value(self):
        transport = FakeTransport({0x02CF041B: b"\x05\x03\x00\x00"})
        properties = Properties(transport)
        self.assertEqual(properties.verify(0x02CF041B, b"\x05\x03\x00\x00"),
                         b"\x05\x03\x00\x00")

    def test_verify_reports_mismatch(self):
        transport = FakeTransport({0x02CF041B: b"\x22\x01\x00\x00"})
        with self.assertRaises(PropertyError) as ctx:
            Properties(transport).verify(0x02CF041B, b"\x05\x03\x00\x00", stage="after save")
        message = str(ctx.exception)
        self.assertIn("after save", message)
        self.assertIn("22010000", message)
        self.assertIn("05030000", message)

    def test_save_defaults_to_group_0x02cf(self):
        transport = FakeTransport()
        Properties(transport).save()
        self.assertEqual(transport.saves(), [("save", GROUP)])

    def test_save_refuses_other_groups(self):
        transport = FakeTransport()
        with self.assertRaises(PropertyGuardError):
            Properties(transport).save(0x0001)
        self.assertEqual(transport.saves(), [])

    def test_save_wraps_transport_errors(self):
        transport = FakeTransport(fail_save=RuntimeError("save rejected"))
        with self.assertRaises(PropertyError) as ctx:
            Properties(transport).save()
        self.assertIn("0x02CF", str(ctx.exception))

    def test_transport_must_expose_all_three_calls(self):
        class Incomplete:
            def read_backup(self, key):
                return b""

        with self.assertRaises(TypeError):
            Properties(Incomplete())


class _FakeSession:
    """The only attribute cmd_* uses from a CameraSession."""

    def __init__(self, transport):
        self.properties = Properties(transport)


@contextmanager
def _session_using(transport):
    yield _FakeSession(transport)


class IgnoringTransport(FakeTransport):
    """Accepts writes but never applies them: simulates a body that drops it."""

    def write_backup(self, key, data):
        self.calls.append(("write", key, bytes(data)))


class CliFlowTests(unittest.TestCase):
    def _run(self, argv, transport):
        out = io.StringIO()
        with mock.patch.object(cli, "_session", lambda args: _session_using(transport)):
            with redirect_stdout(out), redirect_stderr(out):
                code = cli.main(argv)
        return code, out.getvalue()

    def test_functions_is_offline(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = cli.main(["functions"])
        self.assertEqual(code, 0)
        self.assertIn("0x00000305", out.getvalue())
        self.assertIn("not known yet", out.getvalue())

    def test_list_prints_values_and_names(self):
        transport = FakeTransport({
            0x02CF041B: b"\x22\x01\x00\x00",
            0x02CF041C: b"\x00\x03\x00\x00",
        })
        code, output = self._run(
            ["list", "--from", "0x041B", "--to", "0x041C"], transport)
        self.assertEqual(code, 0)
        self.assertIn("0x02CF041B", output)
        self.assertIn("Focus Mode", output)
        self.assertIn("APS-C/Full-frame select", output)
        self.assertIn("read only", output)
        self.assertEqual(transport.writes(), [])

    def test_bind_writes_saves_and_writes_the_receipt_first(self):
        transport = FakeTransport({0x02CF041B: b"\x22\x01\x00\x00"})
        with tempfile.TemporaryDirectory() as tmp:
            code, output = self._run(
                ["bind", "--slot", "0x041B", "--function-id", "0x305",
                 "--receipt-dir", tmp],
                transport,
            )
            self.assertEqual(code, 0)
            self.assertIn("power-cycle the camera to apply", output)
            receipts = list(Path(tmp).glob("*.json"))
            self.assertEqual(len(receipts), 1)
            record = json.loads(receipts[0].read_text(encoding="utf-8"))
            self.assertEqual(record["kind"], "bind")
            self.assertEqual(record["before"]["hex"], "22010000")
            self.assertEqual(record["after"]["hex"], "05030000")
            self.assertEqual(record["readback"], {
                "after_write": "05030000", "after_save": "05030000"})
            self.assertEqual(transport.writes(),
                             [("write", 0x02CF041B, b"\x05\x03\x00\x00")])
            self.assertEqual(transport.saves(), [("save", GROUP)])

    def test_bind_warns_about_an_unknown_function_id_but_still_writes(self):
        transport = FakeTransport({0x02CF041B: b"\x22\x01\x00\x00"})
        with tempfile.TemporaryDirectory() as tmp:
            code, output = self._run(
                ["bind", "--slot", "0x041B", "--function-id", "0x1234",
                 "--receipt-dir", tmp],
                transport,
            )
            self.assertEqual(code, 0)
            self.assertIn("not in the known compact-id table", output)
            self.assertEqual(transport.writes(),
                             [("write", 0x02CF041B, b"\x34\x12\x00\x00")])

    def test_bind_refuses_unverified_slot_without_force(self):
        transport = FakeTransport({0x02CF0420: b"\x5d\x03\x00\x00"})
        with tempfile.TemporaryDirectory() as tmp:
            code, output = self._run(
                ["bind", "--slot", "0x0420", "--function-id", "0x305",
                 "--receipt-dir", tmp],
                transport,
            )
            self.assertEqual(code, 2)
            self.assertIn("--force", output)
            self.assertEqual(transport.writes(), [])
            self.assertEqual(list(Path(tmp).glob("*.json")), [])

    def test_bind_accepts_unverified_slot_with_force(self):
        transport = FakeTransport({0x02CF0420: b"\x5d\x03\x00\x00"})
        with tempfile.TemporaryDirectory() as tmp:
            code, _output = self._run(
                ["bind", "--slot", "0x0420", "--function-id", "0x305",
                 "--force", "--receipt-dir", tmp],
                transport,
            )
            self.assertEqual(code, 0)
            self.assertEqual(transport.writes(),
                             [("write", 0x02CF0420, b"\x05\x03\x00\x00")])

    def test_bind_refuses_all_zero_slot_without_force(self):
        transport = FakeTransport({0x02CF041B: b"\x00\x00\x00\x00"})
        with tempfile.TemporaryDirectory() as tmp:
            code, output = self._run(
                ["bind", "--slot", "0x041B", "--function-id", "0x305",
                 "--receipt-dir", tmp],
                transport,
            )
            self.assertEqual(code, 2)
            self.assertIn("all zero", output)
            self.assertEqual(transport.writes(), [])

    def test_bind_refuses_a_one_byte_slot(self):
        transport = FakeTransport({0x02CF0400: b"\x01"})
        with tempfile.TemporaryDirectory() as tmp:
            code, output = self._run(
                ["bind", "--slot", "0x0400", "--function-id", "0x305",
                 "--force", "--receipt-dir", tmp],
                transport,
            )
            self.assertEqual(code, 2)
            self.assertIn("4-byte compact id", output)
            self.assertEqual(transport.writes(), [])

    def test_bind_refuses_outside_the_scan_range_even_with_force(self):
        transport = FakeTransport({0x02CF0500: b"\x22\x01\x00\x00"})
        with tempfile.TemporaryDirectory() as tmp:
            code, output = self._run(
                ["bind", "--slot", "0x0500", "--function-id", "0x305",
                 "--force", "--receipt-dir", tmp],
                transport,
            )
            self.assertEqual(code, 2)
            self.assertIn("outside the range", output)
            self.assertEqual(transport.writes(), [])

    def test_bind_is_a_no_op_when_the_value_already_matches(self):
        transport = FakeTransport({0x02CF041B: b"\x05\x03\x00\x00"})
        with tempfile.TemporaryDirectory() as tmp:
            code, output = self._run(
                ["bind", "--slot", "0x041B", "--function-id", "0x305",
                 "--receipt-dir", tmp],
                transport,
            )
            self.assertEqual(code, 0)
            self.assertIn("nothing to do", output)
            self.assertEqual(transport.writes(), [])
            self.assertEqual(list(Path(tmp).glob("*.json")), [])

    def test_bind_keeps_the_receipt_when_the_write_does_not_stick(self):
        transport = IgnoringTransport({0x02CF041B: b"\x22\x01\x00\x00"})
        with tempfile.TemporaryDirectory() as tmp:
            code, _output = self._run(
                ["bind", "--slot", "0x041B", "--function-id", "0x305",
                 "--receipt-dir", tmp],
                transport,
            )
            self.assertEqual(code, 1)
            self.assertEqual(transport.saves(), [])
            receipts = list(Path(tmp).glob("*.json"))
            self.assertEqual(len(receipts), 1)
            record = json.loads(receipts[0].read_text(encoding="utf-8"))
            self.assertEqual(record["before"]["hex"], "22010000")
            self.assertIsNone(record["readback"]["after_write"])

    def test_restore_puts_the_old_value_back_and_records_itself(self):
        transport = FakeTransport({0x02CF041B: b"\x22\x01\x00\x00"})
        with tempfile.TemporaryDirectory() as tmp:
            code, _ = self._run(
                ["bind", "--slot", "0x041B", "--function-id", "0x305",
                 "--receipt-dir", tmp],
                transport,
            )
            self.assertEqual(code, 0)
            receipt = next(Path(tmp).glob("*.json"))
            code, output = self._run(
                ["restore", "--receipt", str(receipt), "--receipt-dir", tmp],
                transport,
            )
            self.assertEqual(code, 0)
            self.assertIn("power-cycle the camera to apply", output)
            self.assertEqual(transport.values[0x02CF041B], b"\x22\x01\x00\x00")
            restore_receipts = [p for p in Path(tmp).glob("restore-*.json")]
            self.assertEqual(len(restore_receipts), 1)
            record = json.loads(restore_receipts[0].read_text(encoding="utf-8"))
            self.assertEqual(record["before"]["hex"], "05030000")
            self.assertEqual(record["after"]["hex"], "22010000")
            self.assertIn("restored_from", record)

    def test_restore_refuses_a_receipt_that_does_not_fit(self):
        transport = FakeTransport({0x02CF041B: b"\x22\x01\x00\x00"})
        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / "bind.json"
            receipt.write_text(json.dumps({
                "schema": "bind_button.receipt/1",
                "kind": "bind",
                "property": {"group": "0x02CF", "index": "0x041B",
                             "key": "0x02CF041B"},
                "before": {"hex": "05"},  # 1 byte, slot has 4
                "after": {"hex": "22010000"},
            }), encoding="utf-8")
            code, output = self._run(
                ["restore", "--receipt", str(receipt)], transport)
            self.assertEqual(code, 2)
            self.assertIn("refusing to restore", output)
            self.assertEqual(transport.writes(), [])

    def test_discover_snapshot_then_compare_reports_the_changed_slot(self):
        transport = FakeTransport({
            0x02CF041B: b"\x22\x01\x00\x00",
            0x02CF041C: b"\x00\x03\x00\x00",
        })
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = str(Path(tmp) / "snap.json")
            code, _ = self._run(
                ["discover", "--from", "0x041B", "--to", "0x041C",
                 "--snapshot", snapshot],
                transport,
            )
            self.assertEqual(code, 0)
            transport.values[0x02CF041C] = b"\x05\x03\x00\x00"
            code, output = self._run(
                ["discover", "--from", "0x041B", "--to", "0x041C",
                 "--compare", snapshot],
                transport,
            )
            self.assertEqual(code, 0)
            self.assertIn("0x041C", output)
            self.assertIn("00030000 -> 05030000", output)
            self.assertEqual(transport.writes(), [])


class _FakeUsbError(Exception):
    pass


class _FakeCore:
    """Just enough of usb.core for CameraSession._find/_find_one."""

    USBError = _FakeUsbError

    def __init__(self, devices):
        self.devices = list(devices)

    def find(self, **_kwargs):
        return list(self.devices)


class _FakeDevice:
    def __init__(self, product_id, vendor_id=0x054C):
        self.idVendor = vendor_id
        self.idProduct = product_id


class SessionSelectionTests(unittest.TestCase):
    """The device-selection logic, without opening any USB device."""

    def _session(self, devices):
        from bind_button.session import CameraSession

        session = CameraSession()
        session._core = _FakeCore(devices)
        session._backend = object()
        return session

    def test_no_device_is_a_clear_error(self):
        from bind_button.session import SessionError

        with self.assertRaises(SessionError) as ctx:
            self._session([])._find_one()
        self.assertIn("no camera", str(ctx.exception))

    def test_more_than_one_camera_is_refused(self):
        from bind_button.session import SessionError

        session = self._session([_FakeDevice(0x0E8A), _FakeDevice(0x0336)])
        with self.assertRaises(SessionError) as ctx:
            session._find_one()
        self.assertIn("more than one", str(ctx.exception))

    def test_unrelated_sony_devices_are_ignored(self):
        from bind_button.session import SessionError

        with self.assertRaises(SessionError):
            self._session([_FakeDevice(0x096F)])._find_one()

    def test_post_session_identity_is_explained(self):
        from bind_button.session import SessionError

        with self.assertRaises(SessionError) as ctx:
            self._session([_FakeDevice(0x096F)])._find_one()
        message = str(ctx.exception)
        self.assertIn("054c:096f", message)
        self.assertIn("post-session", message)

    def test_service_identity_is_recognised(self):
        device = _FakeDevice(0x0336)
        self.assertIs(self._session([device])._find_one(), device)

    def test_mass_storage_identity_is_recognised(self):
        device = _FakeDevice(0x0E8A)
        self.assertIs(self._session([device])._find_one(), device)

    def test_enumeration_error_is_wrapped(self):
        from bind_button.session import SessionError

        class BrokenCore(_FakeCore):
            def find(self, **_kwargs):
                raise _FakeUsbError("libusb not initialised")

        session = self._session([])
        session._core = BrokenCore([])
        with self.assertRaises(SessionError) as ctx:
            session._find_one()
        self.assertIn("enumeration failed", str(ctx.exception))


class ApPropertyTransportTests(unittest.TestCase):
    """The transport adapter that turns a SonySenserCamera into three methods."""

    class FakeCamera:
        def __init__(self):
            self.calls = []
            self.value = b"\x22\x01\x00\x00"

        def readBackup(self, key):
            self.calls.append(("read", key))
            return self.value

        def writeBackup(self, key, data):
            self.calls.append(("write", key, bytes(data)))
            self.value = bytes(data)

        def saveBackup(self, group):
            self.calls.append(("save", group))

    def test_delegates_the_three_calls(self):
        from bind_button.session import ApPropertyTransport

        camera = self.FakeCamera()
        transport = ApPropertyTransport(camera)
        self.assertEqual(transport.read_backup(0x02CF041B), b"\x22\x01\x00\x00")
        transport.write_backup(0x02CF041B, b"\x05\x03\x00\x00")
        transport.save_backup(0x02CF)
        self.assertEqual(camera.calls, [
            ("read", 0x02CF041B),
            ("write", 0x02CF041B, b"\x05\x03\x00\x00"),
            ("save", 0x02CF),
        ])

    def test_works_through_properties(self):
        from bind_button.session import ApPropertyTransport

        properties = Properties(ApPropertyTransport(self.FakeCamera()))
        outcome = properties.write(0x02CF041B, b"\x05\x03\x00\x00")
        self.assertTrue(outcome.changed)
        properties.save()
        self.assertEqual(properties.read(0x02CF041B), b"\x05\x03\x00\x00")


if __name__ == "__main__":
    unittest.main()
