# Run iFix Device Support

1. Install Python 3 and Tkinter for your operating system.
2. Install `ideviceinfo` from libimobiledevice. On macOS, run `brew install libimobiledevice`; on Debian or Ubuntu, install `libimobiledevice-utils` with your package manager.
3. Connect and unlock the iPhone or iPad, then accept the Trust prompt if shown.
4. From the iFix directory, run `python3 iFix.py`.
5. Select **Refresh** to inspect the model and software version. Select **Copy diagnostic report** to share a report with device identifiers omitted.

iFix only reads device information. For help with organization management or enrollment, contact the organization that manages the device. See the [project README](../README.md) for details.