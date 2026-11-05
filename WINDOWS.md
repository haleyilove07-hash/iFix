# iFix on Windows 11 (WSL 2)

Windows cannot run this project natively: `palera1n-macos-universal`, `checkra1n.app`
and everything in `device/` are macOS (Mach-O) binaries, and the bypass needs a POSIX
shell, `iproxy` and `sshpass`. The supported way to use iFix on Windows 11 is **WSL 2**:
the GUI and every tool run inside Ubuntu, and WSLg puts the window on your desktop.

## What changed for Windows

- `iFix.py` runs on macOS, Linux and Windows-via-WSL. On Windows it forwards every
  command to `wsl.exe`, so the GUI itself can run from either side.
- Device tools are resolved per platform: the bundled macOS binaries on macOS, the
  system `libimobiledevice` / `libusbmuxd` / `sshpass` packages on Linux and WSL.
- `palera1n` is resolved as `palera1n-macos-universal` (macOS) or
  `palera1n-linux-<arch>` / `palera1n` on PATH (Linux/WSL).
- `mdm.sh` no longer wipes `~/.ssh/known_hosts`; it removes only the `[localhost]:4444`
  tunnel key and reports tool/exit failures instead of silently continuing.
- UDID detection uses a regex instead of slicing between two keys, which failed when
  Linux `ideviceinfo` omitted `UseRaptorCerts`.
- `python3 iFix.py --doctor` checks the toolchain and the connected device without
  opening a window. Use it first when something does not work.

## Install

```powershell
# elevated PowerShell, from the repo root
powershell -ExecutionPolicy Bypass -File .\windows\install.ps1
```

If WSL or Ubuntu was not installed yet, the script installs it and asks you to reboot;
run it once more afterwards. It then installs inside Ubuntu:

```
python3-tk python3-pil libimobiledevice-utils libusbmuxd-tools
libirecovery-utils usbmuxd sshpass
```

and downloads the Linux `palera1n` build into the repo root.

Verify:

```powershell
wsl -e bash -lc "cd $(wsl wslpath -a .) && python3 iFix.py --doctor"
```

## Run

```powershell
windows\run-ifix.cmd
```

## Getting into DFU mode

checkm8 needs the phone in DFU mode, and the timing is what usually fails. Do not
guess it - let iFix count it out:

- **window:** press **dfu helper** and then **start** (works over WSLg too)
- **terminal:** in the Ubuntu shell, `python3 iFix.py --dfu`

Either way the helper counts the sequence (Volume Up, Volume Down, hold Side for
10s, add Volume Down for 5s, release Side and keep Volume Down for 10s), then
polls `irecovery -q` and reports `MODE: DFU` with the ECID - or tells you which
mode the phone actually landed in (normal / recovery) so you can unplug and
retry. `--dfu` exits 0 when DFU is reached and 2 when it is not, so you can
script it. Tkinter is not needed for `--dfu` or `--doctor`.

## Connecting the iPhone

WSL 2 does not see USB devices by default. Share the phone with `usbipd-win`
(installed by the setup script, https://github.com/dorssel/usbipd-win):

```powershell
usbipd list                          # find the Apple bus id
usbipd bind --busid 2-3             # once, elevated
usbipd attach --wsl --busid 2-3     # repeat after unplugging / mode changes
```

Then in WSL:

```bash
sudo usbmuxd -f -v &                 # if usbmuxd is not already running
ideviceinfo | grep UniqueDeviceID    # should print the UDID
```

### Known limitation: DFU over USB/IP

`usbipd` passthrough is **not reliable for DFU/recovery mode**, and checkm8 needs
tight USB timing. Many people never get past the exploit step this way. If
`palera1n` or `checkra1n` cannot enter DFU:

1. Use a **USB-A** cable (USB-C cables often prevent DFU on checkm8 devices).
2. Re-attach after every mode change: `usbipd attach --wsl --busid <id>`.
3. Prefer a bootable Linux USB (`palen1x` for iOS 15/16, `checkn1x` for iOS 12-14)
   and run `mdm.sh` from that live session — same jailbreak, no passthrough involved.
4. As a last resort, a Linux VM with a USB 2.0 controller passed through.

## Supported targets

- checkm8 devices only: A8-A11 (iPhone 6s through iPhone X, plus T2 Macs).
- palera1n: iOS 15.0+. checkra1n: iOS 12.0-14.8.
- `checkra1n` is macOS-only; on Windows/Linux use `palen1x`/`checkn1x` bootable media.
- Only devices you own. The bypass rewrites the MDM configuration profile
  (`CloudConfigurationDetails.plist`) over SSH and reboots userspace.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `WSL is not installed` dialog | Run `windows\install.ps1` elevated, then reboot. |
| `Missing tools` dialog | Re-run `bash windows/setup-wsl.sh` inside Ubuntu. |
| `mdm.sh exited with code 1` | Device not jailbroken, `iproxy` could not bind, or the USB device is not attached to WSL. |
| GUI does not appear | Needs Windows 11 22H2+ (WSLg). Otherwise run `python3 iFix.py` from a terminal with an X server. |
| `No device detected! 0x404` | `usbipd attach --wsl --busid <id>`, then `idevicepair pair`. |

## SSH tunnel (both devices, incl. iPad Air 1 on iOS 12.5.8)

The tunnel is plain OpenSSH plus `iproxy`; checkra1n (iOS 12-14) and palera1n
(iOS 15+) both run dropbear on port **44** with root's password **alpine**, so one
script covers every supported device. In WSL, as root:

    apt install openssh-client sshpass libusbmuxd-tools usbmuxd

`iproxy` must be the libusbmuxd-tools build, which supports device targeting:

    -u, --udid UDID    target a specific device
    -n, --network      device is reachable over Wi-Fi sync instead of USB
    -l, --local        force the USB transport (default)

Verify the tunnel without writing anything, before any bypass:

    ./mdm.sh --test -u <UDID>          # USB
    ./mdm.sh --test -n -u <UDID>       # Wi-Fi sync

That matters here because two iPads are registered in usbmux at once (iPad7,11
and iPad4,2). Run the bypass against one of them:

    ./mdm.sh -u <UDID>                 # USB, default local port 4444
    ./mdm.sh -n -u <UDID> -p 5555      # network device, separate local port

### iPad Air (1st gen / iPad4,2, iOS 12.5.8)

- It is an **A7**: checkm8 applies, but palera1n only handles iOS 15+, so this is
  a **checkra1n** job. iOS 12 needs no fakefs, so `mount -o rw,union,update /`
  succeeds there (and mdm.sh tolerates it failing anyway).
- Some checkra1n releases leave SSH off; enable it when prompted, then confirm
  with `./mdm.sh --test -u <UDID>`.
- Enable Trust + Wi-Fi sync once over USB, then `-n` needs no cable: find the IP
  under Settings > Wi-Fi.
- The profile path is the same on iOS 12 as on 18.x (CloudConfigurationDetails
  under systemgroup.com.apple.configurationprofiles).
