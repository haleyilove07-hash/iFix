#!/usr/bin/env bash
# Installs everything iFix needs *inside* Ubuntu on WSL 2 (also works on a normal
# Debian/Ubuntu machine). Run it from Windows with:
#
#   wsl -e bash -lc "cd \$(wslpath -a 'C:\path\to\iFix') && bash windows/setup-wsl.sh"
#
# or from windows\install.ps1, which does that for you.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

if ! command -v apt-get >/dev/null 2>&1; then
    echo "This script targets Debian/Ubuntu. Install the equivalents of:" >&2
    echo "  python3-tk python3-pil libimobiledevice-utils libusbmuxd-tools usbmuxd sshpass" >&2
    exit 1
fi

echo "==> Installing system packages (sudo will ask for your password)"
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
    libimobiledevice-utils libusbmuxd-tools irecovery usbmuxd \
    sshpass curl ca-certificates
# Tkinter/Pillow are only needed for the GUI window; the CLI modes do not use them
# and some releases no longer ship python3-tk.
sudo apt-get install -y --no-install-recommends python3-tk python3-pil \
    || echo "    WARNING: Tkinter unavailable - the window will not open, --doctor/--dfu/mdm.sh still work" >&2

echo "==> Checking the device tools"
missing=0
for tool in ideviceinfo ideviceenterrecovery irecovery iproxy sshpass; do
    if command -v "$tool" >/dev/null 2>&1; then
        printf '    %-22s %s\n' "$tool" "$(command -v "$tool")"
    else
        printf '    %-22s MISSING\n' "$tool"
        missing=1
    fi
done
[ "$missing" -eq 0 ] || { echo "Some tools are still missing, check the apt output above." >&2; exit 1; }

echo "==> Making sure usbmuxd is running"
if ! pgrep -x usbmuxd >/dev/null 2>&1; then
    sudo mkdir -p /var/run
    sudo usbmuxd -f -v >/tmp/usbmuxd.log 2>&1 &
    sleep 1
    if pgrep -x usbmuxd >/dev/null 2>&1; then
        echo "    usbmuxd started (log: /tmp/usbmuxd.log)"
    else
        echo "    WARNING: usbmuxd did not start, see /tmp/usbmuxd.log" >&2
    fi
else
    echo "    already running"
fi

echo "==> Fetching palera1n (Linux build)"
if command -v palera1n >/dev/null 2>&1 || [ -x "./palera1n-linux-x86_64" ] || [ -x "./palera1n-linux-arm64" ]; then
    echo "    already installed, skipping"
else
    case "$(uname -m)" in
        x86_64|amd64) asset="palera1n-linux-x86_64" ;;
        aarch64|arm64) asset="palera1n-linux-arm64" ;;
        *) echo "    Unsupported architecture $(uname -m), download palera1n manually from https://palera.in/download/" >&2; asset="" ;;
    esac
    if [ -n "${asset:-}" ]; then
        if curl -fsSL --retry 3 -o "$REPO_DIR/$asset" \
            "https://github.com/palera1n/palera1n/releases/latest/download/$asset"; then
            chmod +x "$REPO_DIR/$asset"
            echo "    saved to $REPO_DIR/$asset"
        elif curl -fsSL --retry 3 -o "$REPO_DIR/palera1n.tar.gz" \
            "https://github.com/palera1n/palera1n/releases/latest/download/$asset.tar.gz"; then
            # Newer releases ship a tarball instead of a bare binary.
            rm -rf "$REPO_DIR/.palera1n-extract"
            mkdir -p "$REPO_DIR/.palera1n-extract"
            tar xzf "$REPO_DIR/palera1n.tar.gz" -C "$REPO_DIR/.palera1n-extract"
            if [ -f "$REPO_DIR/.palera1n-extract/palera1n" ]; then
                mv "$REPO_DIR/.palera1n-extract/palera1n" "$REPO_DIR/$asset"
                chmod +x "$REPO_DIR/$asset"
                echo "    saved to $REPO_DIR/$asset (unpacked from tarball)"
            else
                echo "    Tarball did not contain a palera1n binary." >&2
            fi
            rm -rf "$REPO_DIR/.palera1n-extract" "$REPO_DIR/palera1n.tar.gz"
        else
            rm -f "$REPO_DIR/$asset"
            echo "    Automatic download failed. Grab the Linux CLI build from https://palera.in/download/" >&2
            echo "    and save it here as $asset (chmod +x)." >&2
        fi
    fi
fi

chmod +x "$REPO_DIR/mdm.sh" 2>/dev/null || true

echo
echo "==> Done"
echo "Python GUI:  python3 \"$REPO_DIR/iFix.py\"   (from Windows: windows\\run-ifix.cmd)"
echo "Diagnostics: python3 \"$REPO_DIR/iFix.py\" --doctor"
echo
echo "The iPhone must be shared into WSL before iFix can see it:"
echo "  usbipd list"
echo "  usbipd bind --busid <BUSID>        (once, elevated)"
echo "  usbipd attach --wsl --busid <BUSID>"
