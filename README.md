# bind_button

Re-bind a Sony camera button by writing one AP property -- no firmware patch.

**Target**: Sony ILCE-7CM2 (A7C II), verified end to end on real hardware.

**Status**: the mechanism and the write path are proven; the compact function id
for *Continuous Shooting Speed Boost* is **still unknown**. The tool therefore
takes the id as a parameter (`--function-id`) and never guesses one.

## How it works

A custom-key binding is a 4-byte little-endian "compact function id" stored in
AP property group `0x02CF`, in the contiguous slot run `0x0404 .. 0x041F`.
The key is `group << 16 | index`, so AF-ON is `0x02CF041B` and MOVIE is
`0x02CF041C`. The app reads these slots **at boot only**, which is why the tool
writes, saves, reads back, and then asks you to power-cycle the body.

```
bind --slot 0x041B --function-id 0x300
  read 0x02CF041B -> 22010000 (0x122 Focus Mode)
  guard: length must stay 4 bytes, otherwise refuse
  write 22010000 -> 00030000 (0x300 APS-C/Full-frame select)
  read back == new value
  saveBackup(0x02CF)
  read back == new value            -> "power-cycle the camera to apply"
```

Known compact ids: `0x122` Focus Mode, `0x300` APS-C/Full-frame select,
`0x305` Toggle Silent Mode, `0x9C3` Tracking On + Center Area AF.
Write slot `0x041B` = AF-ON, `0x041C` = MOVIE.

## Safety

* **No firmware** is read or written: no DAT, no `appFw.so`, no partition image,
  no capture, no serial number. The only camera-side effect is one 4-byte AP
  property plus one `saveBackup(0x02CF)`.
* **Hard length guard**: a write is refused unless the new payload has exactly
  the length of the value currently stored (`--force` does not override it).
* **Hard range limit**: only group `0x02CF`, only indices `0x0400..0x0430`.
* **Receipt first**: the previous value is written to `receipts/*.json` *before*
  the camera is touched; `restore --receipt` writes it back.
* **USB service sessions can be unstable** on this body: a session may time out,
  reboot the camera, or leave it on the service identity (`054c:096f`). Unplug,
  or pull the battery for ~30 s, then retry.
* Only use this on hardware you own.

## Install

```bat
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

On Windows the body must be bound to WinUSB for **both** USB identities it uses:
`054c:0e8a` (mass storage) and `054c:0336` (service). Use Zadig once per identity.
This stops Windows from mounting the camera as a disk; see `README.zh-CN.md`
section 4.1 for the exact steps and how to undo it. On Linux/macOS use the system
libusb and stop the camera volumes from being mounted.

## Usage

```bat
py -m bind_button.cli functions
py -m bind_button.cli list
py -m bind_button.cli discover
py -m bind_button.cli bind --slot 0x041B --function-id 0x305
py -m bind_button.cli restore --receipt receipts\bind-0x041b-....json
```

* `functions` -- offline table of the known compact ids.
* `list` -- read `0x0400..0x0430` and print every value (read only).
* `discover` -- snapshot, let the user change one assignment, snapshot again and
  print which slot moved (read only; `--snapshot`/`--compare` for two sessions).
* `bind` -- back up the old value, write, read back, save the group, read back
  again, then print `power-cycle the camera to apply`. Nothing changes until the
  body is switched off and on.
* `restore` -- put a receipt's `before` value back and save.

Exit codes: `0` ok, `2` refused by a guard (camera untouched), `1` USB/property
failure, `130` interrupted.

## Tests

```bat
py -m unittest discover -s tests -v
```

All tests are offline: no camera, no pyusb, no USB access.

## Layout

```
bind_button/session.py       USB session (pyusb + Senser auth), pyusb imported lazily
bind_button/properties.py    AP property read/write/save with the guards
bind_button/buttons.py       slot table, compact id table, receipts and snapshots
bind_button/cli.py           argparse front end
bind_button/pmca/            MIT subset of Sony-PMCA-RE (+ PMCA_LICENSE.txt)
docs/DESIGN.zh-CN.md         why a settings write, not a firmware patch; evidence table
docs/RUNTIME-SESSION.zh-CN.md  archived hardware research log
tests/                       offline unit tests
```

## Licensing

`bind_button/pmca/` is a subset of [Sony-PMCA-RE](https://github.com/ma1co/Sony-PMCA-RE)
by ma1co, MIT licensed; the license text is kept in `bind_button/pmca/PMCA_LICENSE.txt`.
Sony and ILCE are trademarks of Sony Corporation; this project is not affiliated
with or endorsed by Sony. The repository's own code has no separate license
declaration (all rights reserved); check before redistributing.
