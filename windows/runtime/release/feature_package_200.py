"""Build and identify the selected A7C II 2.00 feature package.

This fork adds one selection on top of the upstream FL2/FL3 and shutter-sound
features: `burst boost button` (Sony "Cnt Shoot Speed Boost", Japanese
連写速度ブースト).  It is applied by `spotboost_package_200` as an overlay on the
already-built 2.00 package, so the upstream pinned hashes and byte-change counts
stay untouched.  Without `--boost` everything behaves exactly like upstream.
"""

import argparse
import json
from pathlib import Path

import sound_package_200 as sound
import spotboost_package_200 as spotboost

firmware = sound.firmware
MANIFEST_NAME = sound.MANIFEST_NAME
FL23_SHA = "a3076b2bf3b29ffa879bd35904e4002de10e669721b913796025b27bb5e138de"
BOOST_FEATURE = spotboost.FEATURE_ID


def require(ok, message):
    if not ok:
        raise ValueError(message)


def features(fl23, audio_mode, boost=False):
    require(type(fl23) is bool and audio_mode in ("none", "stock", "custom") and
            (fl23 or audio_mode != "none"), "feature selection is empty or invalid")
    require(type(boost) is bool, "burst boost selection is invalid")
    ids = (["fl2_fl3"] if fl23 else []) + (
        [] if audio_mode == "none" else ["electronic_shutter_sound"] +
        (["custom_audio"] if audio_mode == "custom" else []))
    return ids + ([BOOST_FEATURE] if boost else [])


def _base_selection(report):
    fl23 = report.get("fl23") if "fl23" in report else \
        "fl2_fl3" in report.get("base_feature_ids", [])
    return fl23, report.get("audio_mode")


def boost_selected(manifest_path, audio=None):
    """Validate a format-4 selection that carries the burst boost overlay."""
    manifest_path = Path(manifest_path)
    require(not manifest_path.is_symlink() and manifest_path.name == MANIFEST_NAME and
            manifest_path.is_file(), "selected package manifest is missing or linked")
    report = json.loads(manifest_path.read_text(encoding="utf-8"))
    fl23, mode = _base_selection(report)
    ids = features(fl23, mode, True)
    require(report.get("format") == 4 and report.get("feature_ids") == ids and
            report.get("source_official_sha256") == firmware.SOURCE_SHA and
            report.get("package_version") == "2.00" and
            report.get("full_decrypt_verified") is True and
            report.get("output_size") == sound.PACKAGE_SIZE,
            "selected package manifest differs")
    output = Path(report.get("output_path", ""))
    boost_manifest_path = manifest_path.with_name(spotboost.MANIFEST_NAME)
    require(output.name == spotboost.OUTPUT_NAME and
            report.get("output_sha256") == report.get("spot_boost_package_sha256") and
            boost_manifest_path.is_file() and not boost_manifest_path.is_symlink(),
            "burst boost output identity differs")
    boost = json.loads(boost_manifest_path.read_text(encoding="utf-8"))
    require(boost.get("feature") == BOOST_FEATURE and
            boost.get("feature_ids") == ids and
            boost.get("output_sha256") == report.get("output_sha256") and
            boost.get("base_package_sha256") == report.get("base_package_sha256"),
            "burst boost package manifest differs")
    require(boost.get("base_feature_ids") == ids[:-1],
            "burst boost base feature set differs")
    if mode != "none":
        require(report.get("base_package_sha256") ==
                boost.get("base_package_sha256"),
                "burst boost base package differs")
    require(not output.is_symlink() and output.is_file() and
            output.stat().st_size == sound.PACKAGE_SIZE and
            firmware.sha_file(output) == report.get("output_sha256"),
            "selected DAT full hash differs")
    return output, report["output_sha256"]


def selected(manifest_path, audio=None):
    manifest_path = Path(manifest_path)
    require(not manifest_path.is_symlink() and manifest_path.name == MANIFEST_NAME and
            manifest_path.is_file(), "selected package manifest is missing or linked")
    report = json.loads(manifest_path.read_text(encoding="utf-8"))
    if report.get("format") == 4:
        return boost_selected(manifest_path, audio)
    fl23 = report.get("fl23") if "fl23" in report else \
        "fl2_fl3" in report.get("feature_ids", [])
    mode = report.get("audio_mode")
    ids = features(fl23, mode)
    require(report.get("format") == 2 and report.get("feature_ids") == ids and
            report.get("source_official_sha256") == firmware.SOURCE_SHA and
            report.get("package_version") == "2.00" and
            report.get("full_decrypt_verified") is True and
            report.get("output_size") == sound.PACKAGE_SIZE,
            "selected package manifest differs")
    if mode == "none":
        output = Path(report.get("output_path", ""))
        require(fl23 and output.name == firmware.OUT_NAME and
                report.get("output_sha256") == FL23_SHA,
                "FL2/FL3 package identity differs")
    else:
        output = manifest_path.with_name(sound.OUTPUT_NAME)
        expected_base = FL23_SHA if fl23 else firmware.SOURCE_SHA
        require(report.get("base_package_sha256") == expected_base and
                report.get("sound_patch_spec_sha256") == sound.SPEC_SHA and
                type(report.get("volume_percent")) is int and
                1 <= report["volume_percent"] <= 100 and
                (mode == "custom" or report["volume_percent"] == 100),
                "sound package identity differs")
        if mode == "stock":
            require(report.get("source_audio_sha256") is None and
                    report.get("encoded_audio_sha256") is None and
                    report.get("cp", {}).get("sys_sound_sha256") ==
                    sound.spec_data()["original_sys_sound_sha256"] and
                    report.get("registration_length_bytes") == 0x4c0,
                    "stock camera sound was changed")
        else:
            require(all(isinstance(report.get(field), str) and
                        len(report[field]) == 64 for field in
                        ("source_audio_sha256", "encoded_audio_sha256")) and
                    isinstance(report.get("registration_length_bytes"), int) and
                    0 < report["registration_length_bytes"] <= 0xffff,
                    "custom sound proof differs")
            if audio is not None:
                require(firmware.sha_file(Path(audio)) ==
                        report["source_audio_sha256"],
                        "selected custom audio changed")
    require(not output.is_symlink() and output.is_file() and
            output.stat().st_size == sound.PACKAGE_SIZE and
            firmware.sha_file(output) == report.get("output_sha256"),
            "selected DAT full hash differs")
    return output, report["output_sha256"]


def build(official, run_dir, fl23, audio_mode, audio=None, volume_percent=100,
          boost=False):
    official, run_dir = Path(official), Path(run_dir)
    require(not official.is_symlink() and not run_dir.is_symlink(),
            "official DAT or run directory is a link")
    official, run_dir = official.resolve(), run_dir.resolve()
    ids = features(fl23, audio_mode, boost)
    require(official.is_file() and not official.is_symlink() and
            firmware.sha_file(official) == firmware.SOURCE_SHA and
            run_dir.is_dir() and not run_dir.is_symlink(),
            "official 2.01 or private run directory differs")
    manifest = run_dir / MANIFEST_NAME
    if audio_mode == "none":
        require(audio is None and volume_percent == 100,
                "FL2/FL3-only selection has sound options")
        output = firmware.build(official)
        require(firmware.sha_file(output) == FL23_SHA,
                "FL2/FL3 output hash differs")
        base_report = {"format": 2, "feature_ids": ids[:-1] if boost else ids,
                       "fl23": True, "audio_mode": "none", "volume_percent": 100,
                       "source_official_sha256": firmware.SOURCE_SHA,
                       "output_path": str(output), "output_sha256": FL23_SHA,
                       "output_size": sound.PACKAGE_SIZE,
                       "package_version": "2.00", "full_decrypt_verified": True,
                       "camera_access": False}
    else:
        output, base_report = sound.build(official, fl23, audio_mode, audio,
                                          volume_percent, run_dir / sound.OUTPUT_NAME)
        require(base_report["feature_ids"] == (ids[:-1] if boost else ids),
                "built sound features differ")
    if not boost:
        if not manifest.exists():
            with manifest.open("x", encoding="utf-8") as stream:
                json.dump(base_report, stream, indent=2)
                stream.write("\n")
        verified, digest = selected(manifest, audio)
        require(verified == output and
                digest == base_report["output_sha256"],
                "selected package does not match its builder")
        return verified, manifest

    boost_output, boost_report = spotboost.build(output, run_dir)
    report = {"format": 4, "feature_ids": ids, "fl23": fl23,
              "audio_mode": audio_mode, "volume_percent": volume_percent,
              "source_official_sha256": firmware.SOURCE_SHA,
              "base_feature_ids": base_report["feature_ids"],
              "base_package_sha256": base_report["output_sha256"],
              "base_package_path": str(output),
              "spot_boost_package_sha256": boost_report["output_sha256"],
              "output_path": str(boost_output),
              "output_sha256": boost_report["output_sha256"],
              "output_size": sound.PACKAGE_SIZE, "package_version": "2.00",
              "full_decrypt_verified": True, "camera_access": False}
    if manifest.exists():
        require(json.loads(manifest.read_text(encoding="utf-8")) == report,
                "existing selected feature plan differs")
    else:
        with manifest.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2)
            stream.write("\n")
    verified, digest = selected(manifest, audio)
    require(verified == boost_output and
            digest == boost_report["output_sha256"],
            "selected burst boost package does not match its builder")
    return verified, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--fl23", action="store_true")
    parser.add_argument("--audio-mode", choices=("none", "stock", "custom"),
                        required=True)
    parser.add_argument("--audio", type=Path)
    parser.add_argument("--volume", type=int, default=100)
    parser.add_argument("--boost", action="store_true",
                        help="also overlay the burst boost button patch")
    args = parser.parse_args()
    output, manifest = build(args.official, args.out_dir, args.fl23,
                             args.audio_mode, args.audio, args.volume,
                             args.boost)
    print(json.dumps({"event": "feature_package_200_built",
                      "output": str(output), "manifest": str(manifest),
                      "sha256": selected(manifest)[1],
                      "feature_ids": features(args.fl23, args.audio_mode,
                                              args.boost),
                      "camera_access": False}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"error: {exc}")
