# Run iFix with Python

Install Python 3, Tkinter, and `ideviceinfo` from libimobiledevice. The Tkinter package may be distributed separately from Python by your operating system.

On macOS, install libimobiledevice with `brew install libimobiledevice`. On Debian or Ubuntu, install `libimobiledevice-utils` with your package manager.

Connect and unlock the device, accept the Trust prompt if asked, and run this from the iFix directory:

```sh
python3 iFix.py
```

Select **Refresh** to check the device. The copied diagnostic report includes the model and software version but excludes the serial number and UDID. This tool is read-only; it cannot change supervision or management enrollment. Contact the managing organization for enrollment help.

See the [project README](../README.md) for requirements and archived-project details.