#!/usr/bin/env bash
# iFix MDM bypass.
#
# Works with the bundled macOS binaries in ./device and with the Linux packages
# used by WSL 2 / Linux:
#   sudo apt install libimobiledevice-utils libusbmuxd-tools usbmuxd sshpass
set -u

# Change the current working directory
cd "$(dirname "$0")" || exit 1

# Prefer a bundled binary only where it can actually execute (macOS), otherwise
# fall back to the system package of the same name.
resolve() {
    if [ -x "./device/$1" ] && [ "$(uname -s)" = "Darwin" ]; then
        printf './device/%s' "$1"
        return 0
    fi
    if command -v "$1" >/dev/null 2>&1; then
        printf '%s' "$1"
        return 0
    fi
    echo "ERROR: $1 not found." >&2
    echo "       Linux/WSL: sudo apt install libimobiledevice-utils libusbmuxd-tools usbmuxd sshpass" >&2
    return 1
}

IPROXY=$(resolve iproxy) || exit 1
SSHPASS=$(resolve sshpass) || exit 1

PLIST="./iFix.plist"
if [ ! -f "$PLIST" ]; then
    echo "ERROR: $PLIST not found next to mdm.sh." >&2
    exit 1
fi

# Only drop the key for the local tunnel, do not wipe the user's known_hosts.
ssh-keygen -R '[localhost]:4444' >/dev/null 2>&1 || true

echo 'Start iproxy'

# Run iproxy in the background
"$IPROXY" 4444:44 >/dev/null 2>&1 &
IPROXY_PID=$!
trap 'kill "$IPROXY_PID" >/dev/null 2>&1' EXIT

sleep 2

if ! kill -0 "$IPROXY_PID" >/dev/null 2>&1; then
    echo 'ERROR: iproxy could not start (port 4444 in use, or no device attached).' >&2
    exit 1
fi

# Rootful fakefs needs this union remount; a rootless jailbreak (the only option
# on iPadOS 16+) keeps / sealed and read-only, which is fine because the profile
# lives on the writable data volume. So a failure here is not fatal.
"$SSHPASS" -p 'alpine' ssh -o StrictHostKeyChecking=no -p 4444 "root@localhost" \
    'mount -o rw,union,update / 2>/dev/null || true'

"$SSHPASS" -p alpine scp -rP 4444 -o StrictHostKeyChecking=no "$PLIST" \
    root@localhost:/private/var/containers/Shared/SystemGroup/systemgroup.com.apple.configurationprofiles/Library/ConfigurationProfiles/CloudConfigurationDetails.plist \
    || exit 1

"$SSHPASS" -p 'alpine' ssh -o StrictHostKeyChecking=no -p 4444 "root@localhost" \
    'launchctl reboot userspace' || exit 1

echo 'Done!'
