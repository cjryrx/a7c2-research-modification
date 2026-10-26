"""Read, write and save AP properties -- with guards that run before every write.

An AP property ("backup" property in Sony's service vocabulary) is addressed by
a 32-bit key.  The high 16 bits select a property group, the low 16 bits are the
index inside that group::

    key = group << 16 | index          e.g. 0x02CF041B -> group 0x02CF, index 0x041B

The tool knows exactly one group (``GROUP``) because that is the only group any
evidence covers.  ``save`` refuses to save anything else.

The transport is any object with three methods::

    read_backup(key) -> bytes
    write_backup(key, data) -> None
    save_backup(group) -> None

:class:`bind_button.session.ApPropertyTransport` supplies the real one over USB;
the unit tests supply a dict-backed fake.  Nothing in this module imports pyusb.

Why the guards exist: ``writeBackup`` takes the property id and the *new bytes*,
and the camera replaces the whole record.  If the new payload were shorter than
the current one, the tail of the record would be left undefined; if it were
longer, bytes would be interpreted that never existed.  Both are ways to corrupt
a settings record, so a length mismatch is a hard refusal here, not a warning.
"""

from __future__ import annotations

from typing import NamedTuple

# The only property group this project has evidence for.  0x02CF holds the
# custom-key binding slots (see bind_button/buttons.py).
GROUP = 0x02CF

# Policy limit, not a protocol limit: this tool only ever writes small slot
# records (4 bytes).  A larger payload means a bug upstream, so refuse it.
MAX_WRITE_BYTES = 16

MAX_INDEX = 0xFFFF
MAX_GROUP = 0xFFFF


class PropertyError(RuntimeError):
    """The camera or the transport failed, or a reply made no sense."""


class PropertyGuardError(PropertyError):
    """A safety guard refused the operation before anything was written."""


class PropertyLengthError(PropertyGuardError):
    """The new value is not the same length as the value currently stored."""


class WriteOutcome(NamedTuple):
    """What ``Properties.write`` did."""

    before: bytes
    after: bytes
    changed: bool


def property_key(index: int, group: int = GROUP) -> int:
    """Return the 32-bit AP property key for ``index`` in ``group``."""
    index = _check_uint(index, "index", MAX_INDEX)
    group = _check_uint(group, "group", MAX_GROUP)
    return group << 16 | index


def split_key(key: int) -> "tuple[int, int]":
    """Split a 32-bit AP property key into ``(group, index)``."""
    key = _check_uint(key, "key", 0xFFFFFFFF)
    return key >> 16, key & 0xFFFF


def format_key(key: int) -> str:
    """``0x02CF041B`` style formatting for logs and receipts."""
    return "0x%08X" % _check_uint(key, "key", 0xFFFFFFFF)


def format_index(index: int) -> str:
    """``0x041B`` style formatting for slot indices."""
    return "0x%04X" % _check_uint(index, "index", MAX_INDEX)


def encode_u32le(value: int) -> bytes:
    """Encode ``value`` as the 4-byte little-endian payload a slot holds."""
    value = _check_uint(value, "value", 0xFFFFFFFF)
    return value.to_bytes(4, "little")


def decode_u32le(data: bytes) -> int:
    """Decode a 4-byte little-endian slot payload."""
    data = as_bytes(data)
    if len(data) != 4:
        raise PropertyLengthError(
            "expected a 4-byte slot value, got %d bytes (%s)"
            % (len(data), format_value(data))
        )
    return int.from_bytes(data, "little")


def as_bytes(data) -> bytes:
    """Coerce a transport reply to ``bytes`` or fail with a useful message."""
    if isinstance(data, bytes):
        return data
    if isinstance(data, (bytearray, memoryview)):
        return bytes(data)
    raise PropertyError(
        "expected bytes from the transport, got %s" % type(data).__name__
    )


def format_value(value) -> str:
    """Render a byte string for humans: hex, plus a length tag."""
    if value is None:
        return "<none>"
    data = as_bytes(value)
    if not data:
        return "<empty>"
    return "%s (%d byte%s)" % (data.hex(), len(data), "" if len(data) == 1 else "s")


def check_write(current: bytes, new: bytes) -> None:
    """Refuse a write that could corrupt the record.

    Raises :class:`PropertyGuardError` for an absent property or an oversized
    payload, and :class:`PropertyLengthError` when the lengths differ.  Returns
    ``None`` when the write is safe to attempt.
    """
    current = as_bytes(current)
    new = as_bytes(new)
    if not new:
        raise PropertyGuardError("refusing to write an empty value")
    if len(new) > MAX_WRITE_BYTES:
        raise PropertyGuardError(
            "refusing to write %d bytes; this tool writes at most %d"
            % (len(new), MAX_WRITE_BYTES)
        )
    if not current:
        raise PropertyGuardError(
            "property currently reads as empty/absent; nothing to overwrite "
            "(use --force only if you have a backup of this property)"
        )
    if len(current) != len(new):
        raise PropertyLengthError(
            "refusing to change the record length: current value is %d bytes, "
            "new value is %d bytes" % (len(current), len(new))
        )


class Properties:
    """The three AP property operations, guarded."""

    def __init__(self, transport, max_write_bytes: int = MAX_WRITE_BYTES):
        for name in ("read_backup", "write_backup", "save_backup"):
            if not callable(getattr(transport, name, None)):
                raise TypeError("transport has no %s() method" % name)
        self._transport = transport
        self._max_write_bytes = int(max_write_bytes)
        if self._max_write_bytes < 1:
            raise ValueError("max_write_bytes must be positive")

    # -- reads -------------------------------------------------------------
    def read(self, key: int) -> bytes:
        """Read one property and return its raw bytes."""
        key = _check_uint(key, "key", 0xFFFFFFFF)
        try:
            value = self._transport.read_backup(key)
        except PropertyError:
            raise
        except Exception as exc:  # noqa: BLE001 - re-raised with the key attached
            raise PropertyError(
                "read %s failed: %s: %s" % (format_key(key), type(exc).__name__, exc)
            ) from exc
        return as_bytes(value)

    def read_index(self, index: int, group: int = GROUP) -> bytes:
        """Read one property by index inside ``group``."""
        return self.read(property_key(index, group))

    def read_many(self, keys) -> "list[tuple[int, bytes, Exception | None]]":
        """Read several properties, keeping per-key failures.

        Returns ``(key, value, error)`` tuples in input order; exactly one of
        ``value``/``error`` is ``None``.  Used by the ``list`` command so one
        absent property does not abort the scan.
        """
        rows = []
        for key in keys:
            try:
                rows.append((key, self.read(key), None))
            except Exception as exc:  # noqa: BLE001 - reported per property
                rows.append((key, None, exc))
        return rows

    # -- writes ------------------------------------------------------------
    def write(self, key: int, data, current: bytes | None = None) -> WriteOutcome:
        """Overwrite one property with ``data`` of exactly the current length.

        ``current`` may be passed when the caller already read the property;
        otherwise it is read here so the length guard always sees the real
        value.  Nothing is written when the guards refuse.
        """
        key = _check_uint(key, "key", 0xFFFFFFFF)
        new = as_bytes(data)
        if len(new) > self._max_write_bytes:
            raise PropertyGuardError(
                "refusing to write %d bytes; this tool writes at most %d"
                % (len(new), self._max_write_bytes)
            )
        before = self.read(key) if current is None else as_bytes(current)
        check_write(before, new)
        if before == new:
            return WriteOutcome(before=before, after=new, changed=False)
        try:
            self._transport.write_backup(key, new)
        except PropertyError:
            raise
        except Exception as exc:  # noqa: BLE001 - re-raised with the key attached
            raise PropertyError(
                "write %s failed: %s: %s" % (format_key(key), type(exc).__name__, exc)
            ) from exc
        return WriteOutcome(before=before, after=new, changed=True)

    def verify(self, key: int, expected: bytes, stage: str = "readback") -> bytes:
        """Read ``key`` back and require it to equal ``expected``."""
        expected = as_bytes(expected)
        value = self.read(key)
        if value != expected:
            raise PropertyError(
                "%s mismatch for %s: expected %s, camera returned %s"
                % (stage, format_key(key), format_value(expected), format_value(value))
            )
        return value

    def save(self, group: int = GROUP) -> None:
        """Ask the service to persist ``group`` (the proven sequence is save(0x02CF))."""
        group = _check_uint(group, "group", MAX_GROUP)
        if group != GROUP:
            raise PropertyGuardError(
                "refusing to save group 0x%04X; this tool only saves 0x%04X"
                % (group, GROUP)
            )
        try:
            self._transport.save_backup(group)
        except PropertyError:
            raise
        except Exception as exc:  # noqa: BLE001 - re-raised with the group attached
            raise PropertyError(
                "save group 0x%04X failed: %s: %s"
                % (group, type(exc).__name__, exc)
            ) from exc


def _check_uint(value, name: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("%s must be an int, got %s" % (name, type(value).__name__))
    if value < 0 or value > maximum:
        raise ValueError("%s out of range: %r" % (name, value))
    return value
