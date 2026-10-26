"""Open a Sony Senser service session and expose the three AP property calls.

This module is the only part of the package that talks to USB.  It is a small,
cleaned-up version of the session skeleton this project used for the hardware
experiments: find the camera, authenticate into the Senser "service" identity,
then keep a ``SonySenserCamera`` object whose ``readBackup`` / ``writeBackup`` /
``saveBackup`` are the only operations the rest of the tool performs.

Sequence (the same two-stage authentication Sony-PMCA-RE uses):

1. the body is plugged in as mass storage (``054c:0e8a`` on an ILCE-7CM2);
2. the Senser auth handshake starts the service and the body re-enumerates as
   ``054c:0336``;
3. authenticate again on the service identity, then send adjust-control packets.

Platform notes:

* POSIX -- pyusb + the system libusb.  The camera must not have its volumes
  mounted; a mounted volume keeps the kernel driver attached and the first
  handshake fails with a confusing timeout.
* Windows -- pyusb needs a libusb DLL (``libusb-package`` supplies one) *and*
  the device must be bound to WinUSB.  That binding is per USB identity, so both
  ``054c:0e8a`` (mass storage) and ``054c:0336`` (service) need it.  See
  ``README.zh-CN.md`` for the one-time Zadig steps and their side effects.

Nothing here is needed for the offline test suite: pyusb is imported lazily, and
``bind_button.properties`` / ``bind_button.buttons`` never import this module.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from .pmca.usb.driver.generic import BaseUsbBackend, GenericUsbException

SONY_VID = 0x054C
#: Mass-storage identity used by an ILCE-7CM2 (A7C II).  Other bodies differ;
#: override it with ``--vendor-pid`` when the body shows another id.
MASS_STORAGE_PIDS = (0x0E8A,)
#: Senser service identity.  Protocol-wide: 0x0336 was seen on the A7C II and
#: the FX30, 0x02A9 is the other id PMCA knows about.
SERVICE_PIDS = (0x0336, 0x02A9)
SERVICE_PID = SERVICE_PIDS[0]
DEFAULT_VENDOR_PID = MASS_STORAGE_PIDS[0]

#: sysfs idProduct strings that belong to this camera family.
_CAMERA_PID_TEXT = frozenset("%04x" % pid for pid in (SERVICE_PIDS + MASS_STORAGE_PIDS))

#: ``readHasp()`` must return this many bytes before any property call is made.
PRODUCT_INFO_LEN = 88


class SessionError(RuntimeError):
    """USB device missing, driver not bound, or authentication failed."""


def _usb():
    """Import pyusb on demand so the pure modules stay importable without it."""
    try:
        import usb.core
        import usb.util
    except ImportError as exc:  # pragma: no cover - depends on the machine
        raise SessionError(
            "pyusb is not installed; run 'pip install -r requirements.txt'"
        ) from exc
    return usb.core, usb.util


def _libusb_backend():
    """Return a pyusb backend, falling back to the bundled libusb DLL."""
    import usb.backend.libusb1

    backend = usb.backend.libusb1.get_backend()
    if backend is not None:
        return backend
    try:
        import libusb_package
    except ImportError as exc:  # pragma: no cover - depends on the machine
        raise SessionError(
            "no libusb backend found; install libusb, or install the "
            "'libusb-package' wheel on Windows"
        ) from exc
    library = libusb_package.get_library_path()
    if not library or not Path(library).is_file():  # pragma: no cover
        raise SessionError("libusb-package did not provide a libusb library")
    backend = usb.backend.libusb1.get_backend(find_library=lambda _: str(library))
    if backend is None:  # pragma: no cover
        raise SessionError("the bundled libusb library could not be loaded")
    return backend


def _mounted_camera_volumes() -> "list[dict]":
    """POSIX only: this camera's block devices that are still mounted.

    A mounted volume holds the kernel driver, and the first authentication then
    times out.  Matching is done through sysfs ancestry so only this camera's
    volumes are ever reported (never a plain ``/dev/sdX`` guess).
    """
    if os.name == "nt" or not Path("/proc/self/mountinfo").is_file():
        return []
    try:
        lines = Path("/proc/self/mountinfo").read_text(errors="replace").splitlines()
    except OSError:  # pragma: no cover - unreadable /proc
        return []
    mounted: "dict[str, list[str]]" = {}
    for line in lines:
        fields = line.split()
        if len(fields) > 4:
            mounted.setdefault(fields[2], []).append(fields[4])
    block_root = Path("/sys/class/block")
    if not block_root.is_dir():  # pragma: no cover - no sysfs
        return []
    volumes = []
    for block in block_root.iterdir():
        try:
            devnum = (block / "dev").read_text().strip()
        except OSError:
            continue
        if devnum not in mounted:
            continue
        try:
            parents = list(block.resolve().parents)
        except OSError:
            continue
        for parent in parents:
            vendor = parent / "idVendor"
            product = parent / "idProduct"
            try:
                if not (vendor.exists() and product.exists()):
                    continue
                vid = vendor.read_text().strip().lower()
                pid = product.read_text().strip().lower()
            except OSError:
                break
            if vid == "%04x" % SONY_VID and pid in _CAMERA_PID_TEXT:
                volumes.append({"block": block.name, "mounts": mounted[devnum]})
            break
    return volumes


class BulkBackend(BaseUsbBackend):
    """libusb backend for the Sony Senser bulk protocol.

    Only the operations PMCA's ``GenericUsbDriver`` calls are implemented.  USB
    errors are converted to ``GenericUsbException`` with the libusb message kept
    intact: "bulk read of 516 bytes failed: USBTimeoutError ..." is diagnosable,
    a bare ``GenericUsbException()`` is not.
    """

    def __init__(self, device, io_timeout: float = 30.0):
        self.dev = device
        self._core, _ = _usb()
        self.dev.default_timeout = max(1000, int(io_timeout * 1000))

    # -- device identity ---------------------------------------------------
    def getId(self):
        return self.dev.idVendor, self.dev.idProduct

    def getEndpoints(self):
        return self.dev.get_active_configuration()[(0, 0)]

    def reset(self):
        # Release a kernel driver when there is one (POSIX).  On Windows libusb
        # raises NotImplementedError, which means "nothing to detach".
        try:
            if self.dev.is_kernel_driver_active(0):
                self.dev.detach_kernel_driver(0)
        except NotImplementedError:
            pass
        except self._core.USBError as exc:  # pragma: no cover - driver specific
            raise GenericUsbException("cannot detach the kernel driver: %s" % exc) from exc

    def clearHalt(self, ep):
        self.dev.clear_halt(ep)

    # -- data transfers ----------------------------------------------------
    def read(self, ep, length, timeout=None):
        try:
            return self.dev.read(ep, length, timeout).tobytes()
        except self._core.USBError as exc:
            raise GenericUsbException(
                "bulk read of %d bytes failed: %s: %s"
                % (length, type(exc).__name__, exc)
            ) from exc

    def write(self, ep, data):
        try:
            self.dev.write(ep, data)
        except self._core.USBError as exc:
            raise GenericUsbException(
                "bulk write of %d bytes failed: %s: %s"
                % (len(data), type(exc).__name__, exc)
            ) from exc

    def classInterfaceRequestOut(self, request, value, index, data=b""):
        import usb.util

        try:
            self.dev.ctrl_transfer(
                usb.util.CTRL_OUT | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE,
                request, value, index, data,
            )
        except self._core.USBError as exc:
            raise GenericUsbException(
                "class control request 0x%02x failed: %s" % (request, exc)
            ) from exc

    def vendorRequestOut(self, request, value, index, data=b""):
        import usb.util

        try:
            self.dev.ctrl_transfer(
                usb.util.CTRL_OUT | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_OTHER,
                request, value, index, data,
            )
        except self._core.USBError as exc:
            raise GenericUsbException(
                "vendor control request 0x%02x failed: %s" % (request, exc)
            ) from exc


class ApPropertyTransport:
    """The three AP property calls, in the shape ``Properties`` expects."""

    def __init__(self, camera):
        self._camera = camera

    def read_backup(self, key: int) -> bytes:
        return bytes(self._camera.readBackup(int(key)))

    def write_backup(self, key: int, data: bytes) -> None:
        self._camera.writeBackup(int(key), bytes(data))

    def save_backup(self, group: int) -> None:
        self._camera.saveBackup(int(group))


class CameraSession:
    """Context manager around one service session.

    Attributes after ``__enter__``:

    ``device``      the pyusb device object (identity only, no serial is read)
    ``senser``      ``pmca`` ``SonySenserDevice`` transport
    ``camera``      ``SonySenserCamera`` (the raw read/write/save API)
    ``transport``   :class:`ApPropertyTransport`
    ``properties``  :class:`bind_button.properties.Properties` bound to it
    """

    def __init__(
        self,
        vendor_pid: int = DEFAULT_VENDOR_PID,
        timeout: float = 120.0,
        io_timeout: float = 30.0,
    ):
        self.vendor_pid = int(vendor_pid)
        self.timeout = float(timeout)
        self.io_timeout = float(io_timeout)
        self.device = None
        self.senser = None
        self.camera = None
        self.transport = None
        self.properties = None
        self._auth = None
        self._driver = None
        self._usb_util = None
        self._backend = None
        self._core = None

    # -- lifecycle ---------------------------------------------------------
    def __enter__(self) -> "CameraSession":
        try:
            self._open()
        except BaseException:
            self.close()
            raise
        return self

    def __exit__(self, *_exc) -> bool:
        self.close()
        return False

    def close(self) -> None:
        """Best-effort shutdown.

        The body may stay on the service identity (``054c:096f``) after a
        session; that is normal and a power cycle brings it back to mass
        storage.  Errors while stopping are swallowed on purpose so they never
        hide the real failure that led here.
        """
        if self._auth is not None:
            try:
                self._auth.stop()
            except Exception:  # noqa: BLE001 - shutdown must not raise
                pass
            self._auth = None
        if self.device is not None and self._usb_util is not None:
            try:
                self._usb_util.dispose_resources(self.device)
            except Exception:  # noqa: BLE001 - shutdown must not raise
                pass
        self.device = None
        self.senser = None
        self.camera = None
        self.transport = None
        self.properties = None
        self._driver = None

    # -- opening -----------------------------------------------------------
    def _open(self) -> None:
        from .properties import Properties

        self._core, self._usb_util = _usb()
        self._backend = _libusb_backend()

        volumes = _mounted_camera_volumes()
        if volumes:
            summary = ", ".join(
                "%s->%s" % (volume["block"], mount)
                for volume in volumes for mount in volume["mounts"]
            )
            raise SessionError(
                "camera volumes are mounted (%s); unmount them first -- a service "
                "session needs the kernel driver released" % summary
            )

        device = self._find_one()
        if device.idProduct not in SERVICE_PIDS:
            self._authenticate(device)
            self._usb_util.dispose_resources(device)
            # The mass-storage handle and its auth object are dead now; drop
            # them so close() never sends a request into a closed device.
            self._auth = None
            self._driver = None
            device = self._wait_for_service()
        self.device = device
        driver = self._authenticate(device)

        from .pmca.usb.sony import SonySenserCamera, SonySenserDevice

        self.senser = SonySenserDevice(driver)
        self.camera = SonySenserCamera(self.senser)
        # ProductInfo proves the authenticated service answers; its 88 bytes are
        # deliberately neither stored nor printed (they identify the body).
        product = bytes(self.camera.readHasp())
        if len(product) != PRODUCT_INFO_LEN:
            raise SessionError(
                "ProductInfo replied with %d bytes, expected %d: the service "
                "session is not in a usable state" % (len(product), PRODUCT_INFO_LEN)
            )
        self.transport = ApPropertyTransport(self.camera)
        self.properties = Properties(self.transport)

    def _find(self) -> "list":
        """All cameras claiming one of the ids this tool understands."""
        wanted = {self.vendor_pid} | set(SERVICE_PIDS)
        try:
            devices = list(
                self._core.find(
                    find_all=True, idVendor=SONY_VID, backend=self._backend
                )
            )
        except self._core.USBError as exc:
            raise SessionError("USB enumeration failed: %s" % exc) from exc
        return [device for device in devices if device.idProduct in wanted]

    def _find_one(self):
        devices = self._find()
        if len(devices) > 1:
            raise SessionError(
                "more than one Sony camera matches (%s); disconnect the others"
                % ", ".join("%04x:%04x" % (d.idVendor, d.idProduct) for d in devices)
            )
        if not devices:
            hint = ""
            others = self._other_sony_ids()
            if others:
                hint = (
                    "\n  - found %s with an id this tool does not use; if it is "
                    "054c:096f the body is in its post-session state -- "
                    "power-cycle it" % ", ".join(others)
                )
            raise SessionError(
                "no camera with id %04x:%04x or a service id (%s) was found.\n"
                "  - is the body connected and powered on?\n"
                "  - on Windows, is it bound to WinUSB for *this* USB identity?\n"
                "  - does another program still hold the device?%s"
                % (
                    SONY_VID,
                    self.vendor_pid,
                    ", ".join("%04x" % pid for pid in SERVICE_PIDS),
                    hint,
                )
            )
        return devices[0]

    def _other_sony_ids(self) -> "list[str]":
        """Other Sony USB product ids present, for the 'no camera' message."""
        try:
            devices = list(
                self._core.find(find_all=True, idVendor=SONY_VID, backend=self._backend)
            )
        except Exception:  # noqa: BLE001 - this is only a diagnostic hint
            return []
        known = {self.vendor_pid} | set(SERVICE_PIDS)
        return sorted(
            {"%04x:%04x" % (d.idVendor, d.idProduct) for d in devices
             if d.idProduct not in known}
        )

    def _wait_for_service(self, poll: float = 0.25):
        deadline = time.monotonic() + self.timeout
        last_error = ""
        while time.monotonic() < deadline:
            try:
                for device in self._find():
                    if device.idProduct in SERVICE_PIDS:
                        return device
            except SessionError as exc:
                last_error = str(exc)
            time.sleep(poll)
        raise SessionError(
            "the camera authenticated but never appeared as a service device "
            "(%s) within %.0fs%s.\n"
            "  - unplug and replug, or pull the battery for ~30s, then retry;\n"
            "  - on Windows, the service identity needs its own WinUSB binding."
            % (
                ", ".join("054c:%04x" % pid for pid in SERVICE_PIDS),
                self.timeout,
                ": " + last_error if last_error else "",
            )
        )

    def _authenticate(self, device):
        """Run the Senser auth handshake and return the opened driver."""
        from .pmca.usb.sony import SonySenserAuthDevice

        driver = self._open_driver(device)
        auth = SonySenserAuthDevice(driver)
        auth.start()
        try:
            auth.authenticate()
        except Exception as exc:  # noqa: BLE001 - add the stage to the message
            try:
                auth.stop()
            except Exception:  # noqa: BLE001
                pass
            raise SessionError(
                "Senser authentication failed for %04x:%04x: %s: %s"
                % (device.idVendor, device.idProduct, type(exc).__name__, exc)
            ) from exc
        self._driver = driver
        self._auth = auth
        return driver

    def _open_driver(self, device):
        from .pmca.usb.driver.generic import GenericUsbDriver

        backend = BulkBackend(device, self.io_timeout)
        backend.reset()
        try:
            self._usb_util.claim_interface(device, 0)
        except self._core.USBError as exc:
            raise SessionError(
                "cannot claim interface 0 of %04x:%04x: %s (another program may "
                "be using the camera)" % (device.idVendor, device.idProduct, exc)
            ) from exc
        try:
            return GenericUsbDriver(backend)
        except Exception as exc:  # noqa: BLE001 - no bulk endpoints means no driver
            raise SessionError(
                "the camera exposes no bulk endpoints in its active "
                "configuration: %s" % exc
            ) from exc

    # -- introspection -----------------------------------------------------
    def describe(self) -> dict:
        """Small, serial-free description used by ``--verbose``."""
        info = {
            "vendor_pid": "0x%04X" % self.vendor_pid,
            "service_pids": ["0x%04X" % pid for pid in SERVICE_PIDS],
        }
        if self.device is not None:
            info["connected_id"] = "%04x:%04x" % (
                self.device.idVendor,
                self.device.idProduct,
            )
        return info
