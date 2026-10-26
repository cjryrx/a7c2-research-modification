"""Button binding slots, the compact function id table, and receipt files.

What the hardware evidence says
-------------------------------
* The custom-key bindings are a contiguous run of 4-byte little-endian values at
  AP property indices ``0x0404 .. 0x041F`` (group ``0x02CF``, i.e. keys
  ``0x02CF0404 .. 0x02CF041F``).
* Each 4-byte value is a **compact function id** (``0x122`` = Focus Mode,
  ``0x300`` = APS-C/Full-frame select, ...), not a pointer and not a FUNC id.
* Slots ``0x041B`` (AF-ON) and ``0x041C`` (MOVIE) are verified on an
  ILCE-7CM2 by a write + power-cycle test.
* The app reads these values **at boot only**: writing the property and calling
  ``saveBackup(0x02CF)`` changes the stored value immediately, but the button
  only behaves differently after the body has been power-cycled.

What is *not* known
-------------------
The compact id for "Continuous Shooting Speed Boost" (hold/toggle) has not been
identified.  :data:`KNOWN_FUNCTIONS` therefore does not contain it, and this
module must never gain a guessed entry for it.  The CLI takes the id as a
parameter instead; see ``bind --function-id``.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import NamedTuple

from . import __version__
from .properties import (
    GROUP,
    PropertyLengthError,
    encode_u32le,
    format_index,
    format_key,
    property_key,
)

# ---------------------------------------------------------------------------
# Slot table
# ---------------------------------------------------------------------------

# The contiguous run of custom-key binding slots.  Inside it, each property is
# a 4-byte little-endian compact function id.
SLOT_FIRST = 0x0404
SLOT_LAST = 0x041F
SLOT_COUNT = SLOT_LAST - SLOT_FIRST + 1
SLOT_BYTES = 4

# `list` scans a slightly wider window so a shifted layout is visible instead of
# being silently cut off at the edge of the known run.
LIST_FIRST = 0x0400
LIST_LAST = 0x0430

# Slots whose meaning was confirmed by an end-to-end write + power-cycle test on
# real hardware.  Everything else in the run is a slot, but not yet a named one.
VERIFIED_SLOTS = {
    0x041B: "AF-ON",
    0x041C: "MOVIE",
}


class Function(NamedTuple):
    """One compact function id and its (human) names."""

    compact_id: int
    name: str
    name_zh: str
    note: str = ""

    @property
    def id_text(self) -> str:
        return format_compact_id(self.compact_id)


# Only ids that this project has observed being written by the camera's own
# menu, or that have been proven by an end-to-end test.  Do not add the burst
# boost id here until it is measured: a wrong id silently binds a wrong action.
KNOWN_FUNCTIONS = {
    0x122: Function(
        0x122,
        "Focus Mode",
        "对焦模式",
        "AF-ON was 0x9C3, then 0x122 after the menu change to Focus Mode.",
    ),
    0x300: Function(
        0x300,
        "APS-C/Full-frame select",
        "APS-C / 全画幅选择",
        "End-to-end proof: writing this into 0x041B made AF-ON do it after a reboot.",
    ),
    0x305: Function(
        0x305,
        "Toggle Silent Mode",
        "切换静音模式",
        "MOVIE slot 0x041C read 0x305 before/after the menu change.",
    ),
    0x9C3: Function(
        0x9C3,
        "Tracking On + Center Area AF",
        "跟踪开启 + 中央区域 AF",
        "AF-ON's earlier binding; the camera wrote 0x9C3 into 0x041B.",
    ),
}

# The one id this project is still looking for.  Kept as documentation, never
# as a value: there is no number here on purpose.
UNKNOWN_FUNCTION = (
    "Continuous Shooting Speed Boost (Cnt Sht Spd Bst Hold/Toggle): the compact "
    "id is not known yet and is deliberately absent from KNOWN_FUNCTIONS. "
    "Pass it with --function-id once it has been measured."
)


def format_compact_id(value: int) -> str:
    """Format a compact function id as ``0x00000305``."""
    return "0x%08X" % int(value)


def function_for(compact_id: int) -> "Function | None":
    """Return the table entry for ``compact_id``, or ``None`` if unknown."""
    return KNOWN_FUNCTIONS.get(int(compact_id))


def function_name(compact_id: int) -> str:
    """Human name for a compact id, or ``"-"`` when it is not known yet."""
    entry = function_for(compact_id)
    return entry.name if entry is not None else "-"


def encode_function_id(value: int) -> bytes:
    """Encode a compact function id as the 4-byte little-endian slot value.

    ``0x300`` becomes ``00 03 00 00`` -- this matches the raw bytes observed in
    a full-group dump (``0x305 -> 0x300`` was ``05030000 -> 00030000``).
    """
    data = encode_u32le(value)
    if len(data) != SLOT_BYTES:  # pragma: no cover - encode_u32le guarantees it
        raise PropertyLengthError("compact id must encode to 4 bytes")
    return data


def decode_function_id(data: bytes) -> int:
    """Decode a 4-byte little-endian slot value into a compact function id."""
    data = bytes(data)
    if len(data) != SLOT_BYTES:
        raise PropertyLengthError(
            "a slot value must be 4 bytes, got %d (%s)" % (len(data), data.hex())
        )
    return int.from_bytes(data, "little")


def in_slot_run(index: int) -> bool:
    """True when ``index`` is inside the custom-key binding run."""
    return SLOT_FIRST <= int(index) <= SLOT_LAST


def in_list_range(index: int) -> bool:
    """True when ``index`` is inside the window the ``list`` command scans."""
    return LIST_FIRST <= int(index) <= LIST_LAST


def slot_indices() -> "list[int]":
    """All custom-key slot indices, in order."""
    return list(range(SLOT_FIRST, SLOT_LAST + 1))


def list_indices() -> "list[int]":
    """All indices the ``list`` command scans, in order."""
    return list(range(LIST_FIRST, LIST_LAST + 1))


def slot_key(index: int) -> int:
    """AP property key of a slot index."""
    return property_key(index, GROUP)


def describe_slot(index: int) -> str:
    """Short annotation used by the CLI tables."""
    index = int(index)
    if index in VERIFIED_SLOTS:
        return "custom-key slot, %s (verified)" % VERIFIED_SLOTS[index]
    if in_slot_run(index):
        return "custom-key slot"
    return ""


def empty_slot(value: bytes) -> bool:
    """A slot that reads as all zero has no binding assigned."""
    return bool(value) and not any(value)


# ---------------------------------------------------------------------------
# Receipts and snapshots
# ---------------------------------------------------------------------------

RECEIPT_SCHEMA = "bind_button.receipt/1"
SNAPSHOT_SCHEMA = "bind_button.snapshot/1"
RECEIPT_KINDS = ("bind", "restore")


class ReceiptError(ValueError):
    """A receipt or snapshot file is missing, malformed, or the wrong version."""


def utc_now() -> str:
    """UTC timestamp used in receipts and file names."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _value_record(data: bytes) -> dict:
    data = bytes(data)
    record = {"hex": data.hex(), "bytes": len(data)}
    if len(data) == SLOT_BYTES:
        compact = decode_function_id(data)
        entry = function_for(compact)
        record["compact_id"] = format_compact_id(compact)
        record["function"] = entry.name if entry is not None else None
        record["known_id"] = entry is not None
    return record


def build_receipt(
    kind: str,
    index: int,
    before: bytes,
    after: bytes,
    *,
    forced: bool = False,
    note: str = "",
    extra: "dict | None" = None,
) -> dict:
    """Build the JSON record that makes a write reversible.

    ``before`` is the value found in the slot before this operation -- for a
    ``bind`` that is the binding to restore, which is why the record is written
    to disk *before* the camera is touched.
    """
    if kind not in RECEIPT_KINDS:
        raise ValueError("kind must be one of %r" % (RECEIPT_KINDS,))
    index = int(index)
    record = {
        "schema": RECEIPT_SCHEMA,
        "kind": kind,
        "created_utc": utc_now(),
        "tool": {"name": "bind_button", "version": __version__},
        "property": {
            "group": "0x%04X" % GROUP,
            "index": format_index(index),
            "key": format_key(slot_key(index)),
        },
        "before": _value_record(before),
        "after": _value_record(after),
        "forced": bool(forced),
        "note": note or "",
    }
    if extra:
        record.update(extra)
    return record


def receipt_filename(kind: str, index: int, when: "str | None" = None) -> str:
    """``bind-0x041b-20261026T131500Z.json`` style file name."""
    stamp = (when or utc_now()).replace("-", "").replace(":", "")
    if not stamp.endswith("Z"):
        stamp += "Z"
    return "%s-%s-%s.json" % (kind, format_index(index).lower(), stamp)


def save_receipt(directory, record: dict, filename: "str | None" = None,
                 overwrite: bool = False) -> Path:
    """Write ``record`` under ``directory`` and return the path.

    The file is written as UTF-8 JSON with ``ensure_ascii=False`` so the Chinese
    notes stay readable.  It never contains a serial number: nothing in this
    tool reads one.

    Without ``overwrite`` an existing file is never replaced; a ``-1``, ``-2``
    suffix is added instead, so two binds in the same second keep both backups.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    name = filename or receipt_filename(record["kind"], receipt_index(record))
    path = directory / name
    if not overwrite:
        stem, suffix = Path(name).stem, (Path(name).suffix or ".json")
        counter = 1
        while path.exists():
            path = directory / ("%s-%d%s" % (stem, counter, suffix))
            counter += 1
    text = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")
    return path


def load_receipt(path) -> dict:
    """Load and validate a receipt file.

    Validation is deliberately strict: this file is the only backup of the
    previous binding, so a wrong or truncated one must fail loudly instead of
    writing something plausible.
    """
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ReceiptError("cannot read receipt %s: %s" % (path, exc)) from exc
    try:
        record = json.loads(text)
    except ValueError as exc:
        raise ReceiptError("receipt %s is not valid JSON: %s" % (path, exc)) from exc
    if not isinstance(record, dict):
        raise ReceiptError("receipt %s must contain a JSON object" % path)
    if record.get("schema") != RECEIPT_SCHEMA:
        raise ReceiptError(
            "receipt %s has schema %r, expected %r"
            % (path, record.get("schema"), RECEIPT_SCHEMA)
        )
    if record.get("kind") not in RECEIPT_KINDS:
        raise ReceiptError("receipt %s has an unknown kind" % path)

    prop = record.get("property")
    if not isinstance(prop, dict):
        raise ReceiptError("receipt %s has no 'property' object" % path)
    index = _parse_hex_int(prop.get("index"), "property.index", path)
    key = _parse_hex_int(prop.get("key"), "property.key", path)
    if not in_slot_run(index) and not in_list_range(index):
        raise ReceiptError(
            "receipt %s points at index %s, outside the scanned range"
            % (path, format_index(index))
        )
    if key != slot_key(index):
        raise ReceiptError(
            "receipt %s is inconsistent: key %s does not match index %s"
            % (path, format_key(key), format_index(index))
        )
    for field in ("before", "after"):
        block = record.get(field)
        if not isinstance(block, dict):
            raise ReceiptError("receipt %s has no '%s' value" % (path, field))
        _parse_hex_bytes(block.get("hex"), "%s.hex" % field, path)
    return record


def receipt_index(record: dict) -> int:
    """Slot index recorded in a receipt."""
    return _parse_hex_int(record["property"]["index"], "property.index", "<record>")


def receipt_key(record: dict) -> int:
    """AP property key recorded in a receipt."""
    return _parse_hex_int(record["property"]["key"], "property.key", "<record>")


def receipt_before(record: dict) -> bytes:
    """The value that was in the slot before the recorded operation."""
    return _parse_hex_bytes(record["before"]["hex"], "before.hex", "<record>")


def receipt_after(record: dict) -> bytes:
    """The value the recorded operation wrote."""
    return _parse_hex_bytes(record["after"]["hex"], "after.hex", "<record>")


def _parse_hex_int(text, field: str, path) -> int:
    if not isinstance(text, str) or not text.strip():
        raise ReceiptError("receipt %s: %s is not a hex string" % (path, field))
    try:
        return int(text, 16)
    except ValueError as exc:
        raise ReceiptError(
            "receipt %s: %s is not a hex integer (%r)" % (path, field, text)
        ) from exc


def _parse_hex_bytes(text, field: str, path, allow_empty: bool = False) -> bytes:
    if not isinstance(text, str):
        raise ReceiptError("receipt %s: %s is not a string" % (path, field))
    text = text.strip()
    if not text:
        if allow_empty:
            return b""
        raise ReceiptError("receipt %s: %s is empty" % (path, field))
    if len(text) % 2:
        raise ReceiptError("receipt %s: %s has an odd number of hex digits" % (path, field))
    try:
        return bytes.fromhex(text)
    except ValueError as exc:
        raise ReceiptError(
            "receipt %s: %s is not valid hex (%r)" % (path, field, text)
        ) from exc


def build_snapshot(values: "dict[int, bytes | None]", errors: "dict[int, str] | None" = None) -> dict:
    """Build the JSON record used by ``discover`` to diff two scans."""
    return {
        "schema": SNAPSHOT_SCHEMA,
        "created_utc": utc_now(),
        "tool": {"name": "bind_button", "version": __version__},
        "first": format_index(LIST_FIRST),
        "last": format_index(LIST_LAST),
        "values": {
            format_index(index): bytes(value).hex()
            for index, value in sorted(values.items())
            if value is not None
        },
        "errors": {
            format_index(index): str(message)
            for index, message in sorted((errors or {}).items())
        },
    }


def save_snapshot(path, record: dict) -> Path:
    """Write a snapshot JSON file."""
    path = Path(path)
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_snapshot(path) -> "tuple[dict[int, bytes], dict[int, str], dict]":
    """Load a snapshot and return ``(values, errors, record)``."""
    path = Path(path)
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ReceiptError("cannot read snapshot %s: %s" % (path, exc)) from exc
    except ValueError as exc:
        raise ReceiptError("snapshot %s is not valid JSON: %s" % (path, exc)) from exc
    if not isinstance(record, dict) or record.get("schema") != SNAPSHOT_SCHEMA:
        raise ReceiptError(
            "snapshot %s has schema %r, expected %r"
            % (path, record.get("schema") if isinstance(record, dict) else None,
               SNAPSHOT_SCHEMA)
        )
    values, errors = {}, {}
    for text_index, text_value in (record.get("values") or {}).items():
        index = _parse_hex_int(text_index, "values key", path)
        values[index] = _parse_hex_bytes(
            text_value, "values[%s]" % text_index, path, allow_empty=True
        )
    for text_index, message in (record.get("errors") or {}).items():
        index = _parse_hex_int(text_index, "errors key", path)
        errors[index] = str(message)
    return values, errors, record


def diff_snapshots(before: "dict[int, bytes]", after: "dict[int, bytes]") -> "list[tuple[int, bytes, bytes]]":
    """Indices whose value differs between two snapshots."""
    changed = []
    for index in sorted(set(before) & set(after)):
        if before[index] != after[index]:
            changed.append((index, before[index], after[index]))
    return changed


def receipt_path_hint(directory) -> str:
    """Platform-neutral hint used in help text."""
    return str(Path(directory) / "bind-<slot>-<utc>.json")
