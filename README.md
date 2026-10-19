# iFix Device Support

iFix is a small, read-only desktop tool for checking the model and software version of a connected iPhone or iPad. It can copy a support report without including the device serial number or UDID.

This project is archived and is not affiliated with Apple. Its original jailbreak and management-bypass tools are obsolete and are not part of the supported app. iFix does not remove, modify, or circumvent supervision or mobile-device-management enrollment. For an organization-managed device, contact the organization that enrolled it.

## Requirements

- Python 3
- Tkinter, commonly provided by your operating system's Python package
- `ideviceinfo` from libimobiledevice

On macOS, install libimobiledevice with `brew install libimobiledevice`. On Debian or Ubuntu, install `libimobiledevice-utils` with your package manager. Connect and unlock the device, then accept the Trust prompt if it appears.

## Run

From this directory, run:

```sh
python3 iFix.py
```

To build an executable Python app bundle without extra build dependencies:

```sh
./build.sh
./dist/iFix.pyz
```

The `.pyz` bundle still requires Python 3 with Tkinter and the separately installed `ideviceinfo` command. It is not a standalone native binary.

On Linux Mint, build an installable package with:

```sh
./build-deb.sh
```

This creates `dist/ifix_1.0.0-1_all.deb` with a desktop-menu entry. Install it using Software Manager or run `sudo apt install ./dist/ifix_1.0.0-1_all.deb`. APT resolves the declared runtime dependencies: `python3`, `python3-tk`, and `libimobiledevice-utils`. Launch **iFix Device Support** from the application menu or run `ifix`.

Both build scripts use the current Git commit time for stable archive timestamps. Set `SOURCE_DATE_EPOCH` to a Unix timestamp to provide a release-specific build time.

## Test

Run the read-only diagnostic tests with Python's standard library:

```sh
python3 -m unittest discover -s tests -v
```

Use **Refresh** to check the connected device. **Copy diagnostic report** copies the model, iOS version, build, device class, and computer version; identifying device IDs are excluded. The app only reads device information and does not make changes to the device.

If the device is managed by a school or employer, ask its administrator for help with enrollment or removal. For other device issues, visit [Apple Support](https://support.apple.com/contact).

## Archived files

The bundled jailbreak and recovery executables are old macOS binaries. They are not maintained, are not required for device diagnostics, and will not run on Linux. Use current software from its official project and follow the device owner's or administrator's policies.