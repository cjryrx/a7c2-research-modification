"""Command line front end: read slots, identify a button's slot, bind, restore.

Run it as a module so the package is importable::

    py -m bind_button.cli functions
    py -m bind_button.cli list
    py -m bind_button.cli discover
    py -m bind_button.cli bind --slot 0x041B --function-id 0x305
    py -m bind_button.cli restore --receipt receipts/bind-0x041b-....json

``functions`` is offline and safe.  Everything else opens a USB service session,
which is a read for ``list``/``discover`` and a write only for ``bind`` and
``restore``.  No command touches firmware, a partition image, or a file on the
camera's storage: the only camera-side effect is one 4-byte AP property plus the
group save, exactly as documented in docs/DESIGN.zh-CN.md.
"""

from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager
from pathlib import Path

from . import __version__
from .buttons import (
    KNOWN_FUNCTIONS,
    LIST_FIRST,
    LIST_LAST,
    SLOT_BYTES,
    SLOT_FIRST,
    SLOT_LAST,
    UNKNOWN_FUNCTION,
    ReceiptError,
    build_receipt,
    build_snapshot,
    decode_function_id,
    describe_slot,
    diff_snapshots,
    empty_slot,
    encode_function_id,
    format_compact_id,
    function_for,
    in_list_range,
    in_slot_run,
    load_receipt,
    load_snapshot,
    receipt_before,
    receipt_index,
    save_receipt,
    save_snapshot,
    slot_key,
)
from .properties import (
    GROUP,
    PropertyError,
    PropertyGuardError,
    Properties,
    format_index,
    format_key,
    format_value,
    property_key,
)
from .session import DEFAULT_VENDOR_PID, CameraSession, SessionError

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_REFUSED = 2

POWER_CYCLE_MESSAGE = (
    "power-cycle the camera to apply: turn it OFF, then ON.  The app reads the\n"
    "key bindings only at boot, so nothing changes until the body restarts."
)


class Refused(Exception):
    """A guard refused the request before the camera was touched."""


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _hex_int(text: str) -> int:
    """argparse type: accept ``0x041B``, ``1051`` and ``0b10000011011``."""
    try:
        value = int(text, 0)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError(
            "expected an integer such as 0x041B or 1051, got %r" % (text,)
        )
    if value < 0:
        raise argparse.ArgumentTypeError("expected a non-negative integer, got %r" % (text,))
    return value


def _hex_u32(text: str) -> int:
    value = _hex_int(text)
    if value > 0xFFFFFFFF:
        raise argparse.ArgumentTypeError("value does not fit in 32 bits: %r" % (text,))
    return value


def _error(message: str, code: int) -> int:
    print("error: %s" % message, file=sys.stderr)
    return code


def _verbose(args, message: str) -> None:
    if getattr(args, "verbose", False):
        print("# %s" % message, file=sys.stderr)


@contextmanager
def _session(args):
    """Open a camera session and give the caller its ``Properties``."""
    session = CameraSession(
        vendor_pid=args.vendor_pid,
        timeout=args.timeout,
        io_timeout=args.io_timeout,
    )
    with session:
        _verbose(args, "session %s" % session.describe())
        yield session


def _scan(properties: Properties, indices) -> "tuple[dict[int, bytes], dict[int, str]]":
    """Read every index, keeping per-index failures instead of aborting."""
    values: "dict[int, bytes]" = {}
    errors: "dict[int, str]" = {}
    for key, value, error in properties.read_many(property_key(index) for index in indices):
        index = key & 0xFFFF
        if error is not None:
            errors[index] = "%s: %s" % (type(error).__name__, error)
        else:
            values[index] = value
    return values, errors


def _short_value(value: "bytes | None") -> str:
    if value is None:
        return "<error>"
    if not value:
        return "<empty>"
    text = value.hex()
    if len(text) > 24:
        text = text[:24] + "..."
    return text


def _id_and_name(value):
    """``(compact id text, function name)`` for a 4-byte slot value."""
    if value is None or len(value) != SLOT_BYTES:
        return "-", "-"
    compact = decode_function_id(value)
    return format_compact_id(compact), function_for(compact).name if function_for(compact) else "-"


def _print_slot_table(values: "dict[int, bytes]", errors: "dict[int, str]", indices) -> None:
    print("%-7s %-12s %-26s %-12s %-34s %s"
          % ("idx", "property", "value", "compact id", "function", "note"))
    for index in indices:
        if index in errors:
            print("%-7s %-12s %-26s %-12s %-34s %s"
                  % (format_index(index), format_key(slot_key(index)),
                     "<error>", "-", "-", errors[index]))
            continue
        value = values.get(index)
        compact, name = _id_and_name(value)
        print("%-7s %-12s %-26s %-12s %-34s %s"
              % (format_index(index), format_key(slot_key(index)),
                 _short_value(value), compact, name, describe_slot(index)))


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def cmd_functions(args) -> int:
    print("Known compact function ids (AP group 0x%04X, 4-byte little-endian slot value)" % GROUP)
    print()
    print("%-12s %-10s %-32s %s" % ("id", "bytes", "name (English)", "name (Chinese)"))
    for compact in sorted(KNOWN_FUNCTIONS):
        entry = KNOWN_FUNCTIONS[compact]
        print("%-12s %-10s %-32s %s"
              % (entry.id_text, encode_function_id(compact).hex(), entry.name, entry.name_zh))
    print()
    print("Evidence notes")
    for compact in sorted(KNOWN_FUNCTIONS):
        entry = KNOWN_FUNCTIONS[compact]
        print("  %s  %s" % (entry.id_text, entry.note))
    print()
    print("Not known yet")
    print("  " + UNKNOWN_FUNCTION)
    print()
    print("A value that is not in this table is not automatically wrong: the table only")
    print("lists ids this project has observed or proven.  Use `bind --function-id` with")
    print("the id you are testing; the write is recorded in a receipt either way.")
    return EXIT_OK


def cmd_list(args) -> int:
    indices = list(range(args.first, args.last + 1))
    with _session(args) as session:
        values, errors = _scan(session.properties, indices)
    _print_slot_table(values, errors, indices)
    print()
    print("* custom-key binding slots are %s..%s (4-byte little-endian compact ids)"
          % (format_index(SLOT_FIRST), format_index(SLOT_LAST)))
    if errors:
        print("! %d propert%s could not be read (see the note column)"
              % (len(errors), "y" if len(errors) == 1 else "ies"))
    print("read only; nothing was written.")
    return EXIT_OK


def _print_diff(changed) -> None:
    for index, before, after in changed:
        before_id = decode_function_id(before) if len(before) == SLOT_BYTES else None
        after_id = decode_function_id(after) if len(after) == SLOT_BYTES else None
        line = "%s  %s  %s -> %s" % (
            format_index(index), format_key(slot_key(index)), before.hex(), after.hex())
        if before_id is not None and after_id is not None:
            line += "   (%s -> %s)" % (format_compact_id(before_id), format_compact_id(after_id))
        print(line)
        if before_id is not None and after_id is not None:
            print("        %s -> %s   %s"
                  % (function_for(before_id).name if function_for(before_id) else "unknown id",
                     function_for(after_id).name if function_for(after_id) else "unknown id",
                     describe_slot(index)))
        elif not in_slot_run(index):
            print("        outside the custom-key run; treat this with suspicion")


def cmd_discover(args) -> int:
    indices = list(range(args.first, args.last + 1))

    if args.compare:
        before, before_errors, _record = load_snapshot(args.compare)
        _verbose(args, "loaded %d values (%d errors) from %s"
                 % (len(before), len(before_errors), args.compare))
        with _session(args) as session:
            after, after_errors = _scan(session.properties, indices)
        changed = diff_snapshots(before, after)
        print("compared %s with a fresh scan of %s..%s"
              % (args.compare, format_index(args.first), format_index(args.last)))
        print()
        if changed:
            _print_diff(changed)
            print()
            print("%d slot(s) changed.  Bind to the slot of the button you changed:"
                  % len(changed))
            for index, _before, _after in changed:
                print("    py -m bind_button.cli bind --slot %s --function-id <id>"
                      % format_index(index))
        else:
            _print_no_change_hint()
        if after_errors:
            print()
            print("! %d propert%s could not be read in the fresh scan"
                  % (len(after_errors), "y" if len(after_errors) == 1 else "ies"))
        return EXIT_OK

    with _session(args) as session:
        before, before_errors = _scan(session.properties, indices)
        if args.snapshot:
            path = save_snapshot(args.snapshot, build_snapshot(before, before_errors))
            print("saved %d values and %d errors to %s"
                  % (len(before), len(before_errors), path))
            print()
            print("Next: change ONE custom-key assignment on the camera (and leave the")
            print("menu), then run:")
            print("    py -m bind_button.cli discover --compare %s" % path)
            return EXIT_OK

        print("scanned %d properties (%d errors)." % (len(before), len(before_errors)))
        print()
        print("Now change ONE custom-key assignment on the camera:")
        print("  - pick a button you can identify, e.g. the one you want to re-bind;")
        print("  - assign it any function the menu offers;")
        print("  - leave the menu so the body stores it;")
        print("  - do not unplug the cable.")
        try:
            input("Press Enter when you are done... ")
        except EOFError:
            raise Refused(
                "no interactive input available; use `discover --snapshot FILE` and "
                "then `discover --compare FILE` instead"
            ) from None
        after, after_errors = _scan(session.properties, indices)

    changed = diff_snapshots(before, after)
    print()
    if changed:
        _print_diff(changed)
        print()
        print("%d slot(s) changed.  Bind to the slot of the button you changed:"
              % len(changed))
        for index, _before, _after in changed:
            print("    py -m bind_button.cli bind --slot %s --function-id <id>"
                  % format_index(index))
    else:
        _print_no_change_hint()
    return EXIT_OK


def _print_no_change_hint() -> None:
    print("no slot in the scanned range changed.")
    print("  - did the menu really store the new assignment?  Some items only")
    print("    commit when the menu is left;")
    print("  - the app may hold the new binding in RAM until the body restarts.")
    print("    Power-cycle the camera, then compare two sessions:")
    print("      py -m bind_button.cli discover --snapshot snap-before.json")
    print("      (change the assignment, power-cycle)")
    print("      py -m bind_button.cli discover --compare snap-before.json")


def cmd_bind(args) -> int:
    index = args.slot
    if not in_list_range(index):
        raise Refused(
            "slot %s is outside the range this project has evidence for (%s..%s); "
            "refusing even with --force"
            % (format_index(index), format_index(LIST_FIRST), format_index(LIST_LAST))
        )
    try:
        value = encode_function_id(args.function_id)
    except ValueError as exc:
        raise Refused("bad --function-id: %s" % exc) from None

    key = slot_key(index)
    known = function_for(args.function_id)
    with _session(args) as session:
        properties = session.properties
        try:
            before = properties.read(key)
        except PropertyError as exc:
            raise Refused("cannot read %s: %s" % (format_key(key), exc)) from None
        if len(before) != SLOT_BYTES:
            raise Refused(
                "slot %s holds %d byte(s) (%s), not a 4-byte compact id; refusing "
                "to write into it.\n  A 0-byte property cannot be overwritten "
                "without changing the record length, and this tool never does "
                "that -- --force does not override it."
                % (format_index(index), len(before), format_value(before))
            )

        warnings = []
        if not in_slot_run(index):
            warnings.append(
                "slot %s is outside the custom-key binding run %s..%s, so the "
                "evidence for its meaning is weaker"
                % (format_index(index), format_index(SLOT_FIRST), format_index(SLOT_LAST))
            )
        if empty_slot(before):
            warnings.append("slot %s currently reads as all zero (no binding)" % format_index(index))
        if warnings and not args.force:
            raise Refused(
                "; ".join(warnings)
                + "\n  re-run with --force if you are sure, or pick a slot inside "
                "%s..%s" % (format_index(SLOT_FIRST), format_index(SLOT_LAST))
            )

        if before == value:
            print("%s already holds %s; nothing to do."
                  % (format_key(key), format_value(value)))
            print("If the button does not behave that way yet, power-cycle the camera.")
            return EXIT_OK

        print("slot     %s  (%s)%s"
              % (format_index(index), format_key(key),
                 "  " + describe_slot(index) if describe_slot(index) else ""))
        print("current  %s  %s"
              % (format_value(before),
                 function_for(decode_function_id(before)).name
                 if function_for(decode_function_id(before)) else "unknown compact id"))
        print("new      %s  %s"
              % (format_value(value), known.name if known else "unknown compact id"))
        if known is None:
            print()
            print("note: %s is not in the known compact-id table (see `functions`)."
                  % format_compact_id(args.function_id))
            print("      That is expected while the burst-boost id is still being")
            print("      researched; the write is performed and recorded in the receipt.")
        if args.function_id == 0:
            print()
            print("warning: 0x00000000 most likely clears the binding.")
        for warning in warnings:
            print()
            print("warning: %s (accepted because --force was given)" % warning)

        # The receipt is on disk before the camera is touched: if anything fails
        # from here on, the previous binding is recoverable.
        record = build_receipt(
            "bind", index, before, value,
            forced=bool(args.force),
            note=args.note or "",
            extra={"readback": {"after_write": None, "after_save": None}},
        )
        receipt_path = save_receipt(args.receipt_dir, record)
        print()
        print("receipt  %s" % receipt_path)

        outcome = properties.write(key, value, current=before)
        if not outcome.changed:  # pragma: no cover - the equality check above covers it
            print("write was skipped: the slot already held the requested value")
            return EXIT_OK
        after_write = properties.read(key)
        _verbose(args, "readback after write: %s" % after_write.hex())
        if after_write != value:
            raise PropertyError(
                "the camera did not keep the new value: read back %s, expected %s.\n"
                "Nothing was saved.  The receipt %s still holds the previous value."
                % (format_value(after_write), format_value(value), receipt_path)
            )
        properties.save(GROUP)
        after_save = properties.read(key)
        _verbose(args, "readback after save: %s" % after_save.hex())
        if after_save != value:
            raise PropertyError(
                "the value changed back after save: read back %s, expected %s.\n"
                "The receipt %s still holds the previous value."
                % (format_value(after_save), format_value(value), receipt_path)
            )

        record["readback"] = {"after_write": after_write.hex(), "after_save": after_save.hex()}
        save_receipt(args.receipt_dir, record, filename=receipt_path.name, overwrite=True)

    print()
    print("wrote %s to %s, saved group 0x%04X, read back %s"
          % (format_value(value), format_key(key), GROUP, after_save.hex()))
    print("undo with: py -m bind_button.cli restore --receipt \"%s\"" % receipt_path)
    print()
    print(POWER_CYCLE_MESSAGE)
    return EXIT_OK


def cmd_restore(args) -> int:
    record = load_receipt(args.receipt)
    index = receipt_index(record)
    key = slot_key(index)
    target = receipt_before(record)
    _verbose(args, "receipt %s restores %s to %s"
             % (args.receipt, format_key(key), target.hex()))

    with _session(args) as session:
        properties = session.properties
        try:
            current = properties.read(key)
        except PropertyError as exc:
            raise Refused("cannot read %s: %s" % (format_key(key), exc)) from None
        if len(current) != len(target):
            raise Refused(
                "refusing to restore: the receipt holds a %d-byte value but the slot "
                "now reads %d byte(s)" % (len(target), len(current))
            )
        if current == target:
            print("%s already holds %s; nothing to do."
                  % (format_key(key), format_value(target)))
            return EXIT_OK

        print("slot     %s  (%s)" % (format_index(index), format_key(key)))
        print("current  %s" % format_value(current))
        print("restore  %s  (from %s)" % (format_value(target), args.receipt))

        new_record = build_receipt(
            "restore", index, current, target,
            extra={
                "restored_from": str(Path(args.receipt)),
                "readback": {"after_write": None, "after_save": None},
            },
        )
        receipt_path = save_receipt(args.receipt_dir, new_record)
        print("receipt  %s" % receipt_path)

        properties.write(key, target, current=current)
        after_write = properties.read(key)
        if after_write != target:
            raise PropertyError(
                "the camera did not keep the restored value: read back %s, expected %s"
                % (format_value(after_write), format_value(target))
            )
        properties.save(GROUP)
        after_save = properties.read(key)
        if after_save != target:
            raise PropertyError(
                "the value changed back after save: read back %s, expected %s"
                % (format_value(after_save), format_value(target))
            )
        new_record["readback"] = {"after_write": after_write.hex(), "after_save": after_save.hex()}
        save_receipt(args.receipt_dir, new_record, filename=receipt_path.name, overwrite=True)

    print()
    print("restored %s into %s, saved group 0x%04X, read back %s"
          % (format_value(target), format_key(key), GROUP, after_save.hex()))
    print()
    print(POWER_CYCLE_MESSAGE)
    return EXIT_OK


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="py -m bind_button.cli",
        description=(
            "Bind a Sony camera button to a compact function id by writing one AP "
            "property (group 0x02CF) and saving the group.  The body must be "
            "power-cycled afterwards; the app reads bindings at boot only."
        ),
        epilog=(
            "The compact id for Continuous Shooting Speed Boost is still unknown; "
            "pass any id with --function-id.  See `functions` for the known table "
            "and docs/DESIGN.zh-CN.md for the evidence."
        ),
    )
    parser.add_argument("--version", action="version", version="bind_button " + __version__)
    parser.add_argument("--vendor-pid", type=_hex_int, default=DEFAULT_VENDOR_PID,
                        help="mass-storage USB product id of the body (default 0x%04X)"
                             % DEFAULT_VENDOR_PID)
    parser.add_argument("--timeout", type=float, default=120.0,
                        help="seconds to wait for the service identity (default 120)")
    parser.add_argument("--io-timeout", type=float, default=30.0,
                        help="per USB transfer timeout in seconds (default 30)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="log session and readback detail to stderr")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("functions", help="print the known compact-id table (offline)"
                   ).set_defaults(func=cmd_functions)

    list_parser = sub.add_parser(
        "list", help="read the slot range and print every value (read only)")
    _add_range_arguments(list_parser)
    list_parser.set_defaults(func=cmd_list)

    discover_parser = sub.add_parser(
        "discover",
        help="find which slot belongs to the button you changed (read only)")
    _add_range_arguments(discover_parser)
    group = discover_parser.add_mutually_exclusive_group()
    group.add_argument("--snapshot", type=Path,
                       help="write the current scan to this JSON file and exit")
    group.add_argument("--compare", type=Path,
                       help="diff the current scan against a file written by --snapshot")
    discover_parser.set_defaults(func=cmd_discover)

    bind_parser = sub.add_parser(
        "bind", help="write one compact function id into one slot, then save")
    bind_parser.add_argument("--slot", type=_hex_int, required=True,
                             help="slot index, e.g. 0x041B (AF-ON) or 0x041C (MOVIE)")
    bind_parser.add_argument("--function-id", type=_hex_u32, required=True,
                             help="compact function id, e.g. 0x305 (Toggle Silent Mode)")
    bind_parser.add_argument("--force", action="store_true",
                             help="allow a slot outside 0x0404..0x041F, or a slot whose "
                                  "value is all zeros (4 zero bytes)")
    bind_parser.add_argument("--note", default="",
                             help="free text stored in the receipt")
    bind_parser.add_argument("--receipt-dir", type=Path, default=Path("receipts"),
                             help="where the pre-write backup is written (default ./receipts)")
    bind_parser.set_defaults(func=cmd_bind)

    restore_parser = sub.add_parser(
        "restore", help="put the value from a receipt back and save")
    restore_parser.add_argument("--receipt", type=Path, required=True,
                                help="receipt written by `bind` (its `before` value is restored)")
    restore_parser.add_argument("--receipt-dir", type=Path, default=Path("receipts"),
                                help="where the restore receipt is written (default ./receipts)")
    restore_parser.set_defaults(func=cmd_restore)
    return parser


def _add_range_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--from", dest="first", type=_hex_int, default=LIST_FIRST,
                        help="first index to scan (default 0x%04X)" % LIST_FIRST)
    parser.add_argument("--to", dest="last", type=_hex_int, default=LIST_LAST,
                        help="last index to scan (default 0x%04X)" % LIST_LAST)


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "first", 0) > getattr(args, "last", 0):
        parser.error("--from must not be greater than --to")
    if getattr(args, "last", 0) > 0xFFFF:
        parser.error("--to must fit in a 16-bit index")
    try:
        return args.func(args)
    except Refused as exc:
        return _error(str(exc), EXIT_REFUSED)
    except ReceiptError as exc:
        return _error(str(exc), EXIT_REFUSED)
    except PropertyGuardError as exc:
        return _error(str(exc), EXIT_REFUSED)
    except (SessionError, PropertyError) as exc:
        return _error(str(exc), EXIT_ERROR)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
