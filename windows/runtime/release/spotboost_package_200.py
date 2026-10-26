"""Overlay the "burst boost button" (Sony Cnt Shoot Speed Boost) patch.

This stage runs *after* the author's FL2/FL3 and/or electronic-shutter-sound
build and rewrites only the byte spans declared in `patches_spotboost.json`.
That order is deliberate:

* the upstream builder pins its own plaintext SHA-256 and asserts an exact
  number of changed bytes (86 app / 4 WBI2 / 155 CP), so it must see an
  untouched official 2.01 package;
* every extra change belongs to this file, where it is individually guarded by
  an old-value SHA-256 *and* a 64-byte context SHA-256;
* the package versions and the per-partition `part_image.sum` entries are
  already produced upstream, so this stage only has to refresh the CRC entries
  of the partitions it touched.

The patch data is data, not code: adding or moving a span never changes this
module.  A spec whose `status` is not `ready` is refused, so an unfinished
research note can never produce a package.
"""

import argparse
import json
import mmap
import os
from pathlib import Path
import sys
import zlib

import sound_package_200 as sound

firmware = sound.firmware

ROOT = Path(__file__).resolve().parent
SPEC_PATH = ROOT / "patches_spotboost.json"
OUTPUT_NAME = "BODYDATA_SPOTBOOST_200.DAT"
MANIFEST_NAME = "spotboost_package_200.json"
FEATURE_ID = "burst_boost_button"
PACKAGE_SIZE = sound.PACKAGE_SIZE

PARTITIONS = {"usr": b"dev/nflasha15,", "wbi": b"dev/nflasha5,",
              "cp": b"dev/nflasha8,"}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    import hashlib
    return hashlib.sha256(raw).hexdigest()


def spec_sha():
    return sha(SPEC_PATH.read_bytes())


def spec_data(path=None):
    path = Path(path) if path is not None else SPEC_PATH
    raw = path.read_bytes()
    data = json.loads(raw.decode("utf-8"))
    require(data.get("format") == 1, "spot boost spec format differs")
    require(data.get("id") == FEATURE_ID, "spot boost spec id differs")
    require(data.get("status") in ("ready", "unresolved"),
            "spot boost spec status differs")
    require(isinstance(data.get("bases"), list) and data["bases"],
            "spot boost spec has no base packages")
    for base in data["bases"]:
        require(isinstance(base.get("feature_ids"), list) and
                all(isinstance(item, str) for item in base["feature_ids"]) and
                isinstance(base.get("dat_sha256"), str) and
                len(base["dat_sha256"]) == 64 and
                isinstance(base.get("plain_sha256"), str) and
                len(base["plain_sha256"]) == 64,
                "spot boost base entry differs")
    spans = data.get("spans")
    require(isinstance(spans, list), "spot boost spec has no span list")
    if data["status"] == "ready":
        require(spans, "ready spec has no spans")
        for span in spans:
            require(isinstance(span.get("name"), str) and span["name"],
                    "spot boost span name differs")
            require(span.get("partition") in PARTITIONS,
                    span["name"] + ": unknown partition")
            require(isinstance(span.get("offset"), int) and
                    not isinstance(span["offset"], bool) and span["offset"] >= 0,
                    span["name"] + ": bad offset")
            require(isinstance(span.get("old_sha256"), str) and
                    len(span["old_sha256"]) == 64,
                    span["name"] + ": bad old hash")
            new = bytes.fromhex(span.get("new", ""))
            require(new, span["name"] + ": empty replacement")
            context = span.get("context_size", 0)
            require(isinstance(context, int) and 0 < context <= 0x1000 and
                    span["offset"] >= 64, span["name"] + ": bad context window")
            require(isinstance(span.get("context_sha256"), str) and
                    len(span["context_sha256"]) == 64,
                    span["name"] + ": bad context hash")
            require(isinstance(span.get("why"), str) and span["why"],
                    span["name"] + ": every span needs a documented reason")
    return data


def base_for(dat_sha, data):
    for base in data["bases"]:
        if base["dat_sha256"] == dat_sha:
            return base
    return None


def _partition_geometry(p15, p5, p8):
    return {"usr": p15, "wbi": p5, "cp": p8}


def _check_spans(mm, spans, parts):
    prepared = []
    for span in spans:
        part = parts[span["partition"]]
        at = part.offset_data + span["offset"]
        new = bytes.fromhex(span["new"])
        require(part.offset_data <= at and
                at + len(new) <= part.offset_data + part.size,
                span["name"] + ": span leaves its partition")
        marker_at = at - 64
        marker = bytes(mm[marker_at:marker_at + span["context_size"]])
        old = bytes(mm[at:at + len(new)])
        require(len(marker) == span["context_size"] and
                sha(marker) == span["context_sha256"],
                span["name"] + ": guard window differs")
        require(sha(old) == span["old_sha256"],
                span["name"] + ": source bytes differ")
        require(old != new, span["name"] + ": image is already patched")
        prepared.append((span, at, old, new))
    ordered = sorted(prepared, key=lambda item: item[1])
    for left, right in zip(ordered, ordered[1:]):
        require(left[1] + len(left[3]) <= right[1],
                left[0]["name"] + " overlaps " + right[0]["name"])
    return prepared


def patch_plain(plain, data, base):
    p15, p5, p8, listing = firmware.tar_parts(plain)
    parts = _partition_geometry(p15, p5, p8)
    with plain.open("r+b") as stream:
        mm = mmap.mmap(stream.fileno(), 0)
        try:
            require(bytes(mm[0x20:0x22]) == b"\x00\x02",
                    "spot boost base package is not 2.00")
            old_crc = {name: firmware.crc_window(mm, part.offset_data, part.size)
                       for name, part in parts.items()}
            prepared = _check_spans(mm, data["spans"], parts)
            changed = {"usr": 0, "wbi": 0, "cp": 0}
            for span, at, old, new in prepared:
                mm[at:at + len(new)] = new
                require(bytes(mm[at:at + len(new)]) == new,
                        span["name"] + ": write-back differs")
                changed[span["partition"]] += sum(a != b for a, b in zip(old, new))
            expected = data.get("expected_byte_changes", {})
            for name in changed:
                if name in expected:
                    require(changed[name] == expected[name],
                            "unexpected number of " + name + " changes")
            listed = bytes(mm[listing.offset_data:listing.offset_data + listing.size])
            crc_report = {}
            for name, part in parts.items():
                lines = [line for line in listed.splitlines()
                         if line.endswith(PARTITIONS[name])]
                require(len(lines) == 1 and lines[0].startswith(b"0,") and
                        len(lines[0][2:10]) == 8,
                        name + ": partition checksum entry differs")
                before = int(lines[0][2:10], 16)
                require(before == old_crc[name],
                        name + ": base partition checksum differs")
                after = firmware.crc_window(mm, part.offset_data, part.size)
                crc_at = listing.offset_data + listed.find(lines[0]) + 2
                mm[crc_at:crc_at + 8] = f"{after:08x}".encode("ascii")
                crc_report[name] = {"list": f"{before:08x}", "new": f"{after:08x}"}
            mm.flush()
            return {"byte_changes": changed,
                    "partition_crc32": crc_report,
                    "spans_applied": [span["name"] for span, _, _, _ in prepared]}
        finally:
            mm.close()


def verify_output(output, plain, layout):
    require(firmware.parse_dat(output) == layout,
            "spot boost DAT layout or trailer differs")
    with plain.open("rb") as expected:
        for block in firmware.decoded_blocks(output, layout):
            require(expected.read(len(block)) == block,
                    "spot boost full decrypt differs")
        require(expected.read(1) == b"", "spot boost plaintext length differs")


def preflight(base, spec_path=None):
    """Check base identity and every guarded span without writing a package."""
    base = Path(base).resolve()
    data = spec_data(spec_path)
    require(base.is_file() and not base.is_symlink(), "base package is missing")
    entry = base_for(firmware.sha_file(base), data)
    require(entry is not None, "base package is not declared by the spec")
    require(data["status"] == "ready", "spec status is not ready")
    layout = firmware.parse_dat(base)
    plain = base.with_name(".spotboost_preflight.bin")
    require(not plain.exists(), "stale preflight plaintext present")
    try:
        with plain.open("xb") as stream:
            for block in firmware.decoded_blocks(base, layout):
                stream.write(block)
        require(firmware.sha_file(plain) == entry["plain_sha256"],
                "base plaintext differs")
        p15, p5, p8, listing = firmware.tar_parts(plain)
        parts = _partition_geometry(p15, p5, p8)
        with plain.open("r+b") as stream:
            mm = mmap.mmap(stream.fileno(), 0)
            try:
                prepared = _check_spans(mm, data["spans"], parts)
            finally:
                mm.close()
        return {"base_package_sha256": entry["dat_sha256"],
                "spans_verified": [span["name"] for span, _, _, _ in prepared],
                "byte_changes": {name: sum(
                    sum(a != b for a, b in zip(old, new))
                    for span, _, old, new in prepared
                    if span["partition"] == name)
                    for name in parts}}
    finally:
        plain.unlink(missing_ok=True)


def build(base, output_dir=None, spec_path=None):
    base = Path(base)
    require(base.is_file() and not base.is_symlink(),
            "spot boost base package is missing or linked")
    base = base.resolve()
    data = spec_data(spec_path)
    require(data["status"] == "ready",
            "spot boost patch bytes are not resolved yet; refusing to build")
    base_sha = firmware.sha_file(base)
    entry = base_for(base_sha, data)
    require(entry is not None,
            "spot boost base package is not one of the declared inputs")
    require(base.stat().st_size == PACKAGE_SIZE, "spot boost base length differs")
    output_dir = base.parent if output_dir is None else Path(output_dir)
    require(output_dir.is_dir() and not output_dir.is_symlink(),
            "spot boost output directory differs")
    output = output_dir / OUTPUT_NAME
    manifest = output_dir / MANIFEST_NAME
    require(not output.is_symlink() and not manifest.is_symlink(),
            "spot boost output is a link")

    if output.exists() or manifest.exists():
        require(output.is_file() and manifest.is_file(),
                "incomplete spot boost build; inspect it first")
        report = json.loads(manifest.read_text(encoding="utf-8"))
        require(report.get("spot_boost_spec_sha256") == spec_sha() and
                report.get("base_package_sha256") == base_sha and
                report.get("full_decrypt_verified") is True and
                firmware.sha_file(output) == report.get("output_sha256"),
                "existing spot boost package does not match this spec")
        return output, report

    plain = output_dir / ".spotboost_plain_building.bin"
    temporary = output_dir / ".spotboost_dat_building.bin"
    require(not plain.exists() and not temporary.exists(),
            "stale spot boost build files present")
    try:
        layout = firmware.parse_dat(base)
        with plain.open("xb") as stream:
            for block in firmware.decoded_blocks(base, layout):
                stream.write(block)
            stream.flush()
            os.fsync(stream.fileno())
        require(firmware.sha_file(plain) == entry["plain_sha256"],
                "spot boost base plaintext differs")
        changes = patch_plain(plain, data, entry)
        target_plain_sha = firmware.sha_file(plain)
        dend_crc = firmware.encrypt_from(plain, base, temporary, layout)
        verify_output(temporary, plain, layout)
        output_sha = firmware.sha_file(temporary)
        require(temporary.stat().st_size == PACKAGE_SIZE,
                "spot boost DAT length differs")
        report = {"format": 3,
                  "feature_ids": entry["feature_ids"] + [FEATURE_ID],
                  "feature": FEATURE_ID,
                  "title": data.get("title", FEATURE_ID),
                  "source_official_sha256": firmware.SOURCE_SHA,
                  "base_package_sha256": base_sha,
                  "base_feature_ids": entry["feature_ids"],
                  "spot_boost_spec_sha256": spec_sha(),
                  "output_path": str(output),
                  "output_sha256": output_sha,
                  "output_plain_sha256": target_plain_sha,
                  "output_size": PACKAGE_SIZE,
                  "package_version": "2.00",
                  "full_decrypt_verified": True,
                  "camera_access": False,
                  "dend_crc32": dend_crc,
                  "note": data.get("note", ""),
                  **changes}
        temporary.replace(output)
        manifest.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
        return output, report
    finally:
        plain.unlink(missing_ok=True)
        temporary.unlink(missing_ok=True)


def selected(manifest_path):
    manifest_path = Path(manifest_path)
    require(manifest_path.is_file() and not manifest_path.is_symlink() and
            manifest_path.name == MANIFEST_NAME,
            "selected spot boost manifest is missing or linked")
    report = json.loads(manifest_path.read_text(encoding="utf-8"))
    data = spec_data()
    require(report.get("format") == 3 and report.get("feature") == FEATURE_ID and
            report.get("spot_boost_spec_sha256") == spec_sha() and
            report.get("source_official_sha256") == firmware.SOURCE_SHA and
            report.get("package_version") == "2.00" and
            report.get("full_decrypt_verified") is True and
            report.get("output_size") == PACKAGE_SIZE,
            "selected spot boost manifest differs")
    entry = base_for(report.get("base_package_sha256", ""), data)
    require(entry is not None, "selected spot boost base is not declared")
    require(report.get("feature_ids") == entry["feature_ids"] + [FEATURE_ID],
            "selected spot boost feature set differs")
    output = manifest_path.with_name(OUTPUT_NAME)
    require(output.is_file() and not output.is_symlink() and
            output.stat().st_size == PACKAGE_SIZE and
            firmware.sha_file(output) == report.get("output_sha256"),
            "selected spot boost DAT hash differs")
    return output, report["output_sha256"]


def describe(dat, feature_ids=None):
    """Report the identities a spec `bases` entry needs for an existing package."""
    import hashlib
    dat = Path(dat).resolve()
    require(dat.is_file(), "package is missing")
    layout = firmware.parse_dat(dat)
    plain_digest = hashlib.sha256()
    for block in firmware.decoded_blocks(dat, layout):
        plain_digest.update(block)
    return {"feature_ids": list(feature_ids or []),
            "dat_sha256": firmware.sha_file(dat),
            "plain_sha256": plain_digest.hexdigest(),
            "size": dat.stat().st_size,
            "package_version": _plain_version(dat, layout)}


def _plain_version(dat, layout):
    for block in firmware.decoded_blocks(dat, layout):
        major, minor = block[0x20], block[0x21]
        return "%d.%02d" % (minor, major)
    return "?"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path,
                        help="2.00 package produced by the FL2/FL3 / sound stage")
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--describe", type=Path,
                        help="print the spec `bases` entry for this package")
    parser.add_argument("--preflight", type=Path,
                        help="verify the spec against this base package only")
    args = parser.parse_args()
    if args.describe is not None:
        print(json.dumps(describe(args.describe), indent=2))
        return
    if args.preflight is not None:
        print(json.dumps(preflight(args.preflight, args.spec), indent=2))
        return
    require(args.base is not None, "--base is required unless --describe is used")
    output, report = build(args.base, args.out_dir, args.spec)
    print(json.dumps({"event": "spotboost_package_200_built",
                      "output": str(output),
                      "sha256": report["output_sha256"],
                      "byte_changes": report["byte_changes"],
                      "camera_access": False}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("error:", exc, file=sys.stderr)
        raise SystemExit(1)
