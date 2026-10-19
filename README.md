# iFix Device Support

iFix is a small, read-only desktop tool for checking the model and software version of a connected iPhone or iPad. It can copy a support report without including the device serial number or UDID.

This project is archived and is not affiliated with Apple. Its original jailbreak and management-bypass tools are obsolete and are not part of the supported app. iFix does not remove, modify, or circumvent supervision or mobile-device-management enrollment. For an organization-managed device, contact the organization that enrolled it.

## Fedora 44 requirements

Install the supported runtime dependencies:

```sh
sudo dnf install python3 python3-tkinter libimobiledevice-utils
```

Fedora 44 provides `ideviceinfo` through `libimobiledevice-utils` and provides Tkinter through `python3-tkinter`. citeturn0search5turn0search0

Connect and unlock the device, then accept the Trust prompt if it appears.

## Run

From this directory, run:

```sh
python3 iFix.py
```

Use **Refresh** to check the connected device. **Copy diagnostic report** copies the model, iOS version, build, device class, and computer version; identifying device IDs are excluded. The app only reads device information and does not make changes to the device.

## Build an RPM for Fedora 44

Install the build requirement and create a Fedora RPM:

```sh
sudo dnf install rpm-build
./build-rpm.sh
```

The resulting package is written to `dist/rpm/RPMS/noarch/ifix-device-support-1.0.0-1.noarch.rpm`. Install it with:

```sh
sudo dnf install ./dist/rpm/RPMS/noarch/ifix-device-support-1.0.0-1.noarch.rpm
```

Launch **iFix Device Support** from the application menu or run `ifix`. The package declares `python3`, `python3-tkinter`, and `libimobiledevice-utils` as runtime dependencies.

To build an executable Python app archive without RPM tooling:

```sh
./build.sh
./dist/iFix.pyz
```

The `.pyz` bundle still requires Python 3 with Tkinter and the separately installed `ideviceinfo` command. It is not a standalone native binary.

Both build scripts use the current Git commit time for stable archive timestamps. Set `SOURCE_DATE_EPOCH` to a Unix timestamp to provide a release-specific build time.

## Test

Run the read-only diagnostic tests with Python's standard library:

```sh
python3 -m unittest discover -s tests -v
```

If the device is managed by a school or employer, ask its administrator for help with enrollment or removal. For other device issues, visit Apple Support.

## Archived files

The bundled jailbreak and recovery executables are old macOS binaries. They are not maintained, are not required for device diagnostics, and will not run on Fedora. Use current software from its official project and follow the device owner's or administrator's policies.
