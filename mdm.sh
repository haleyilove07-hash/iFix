#!/usr/bin/env bash
# iFix MDM bypass.
#
# Works with the bundled macOS binaries in ./device and with the Linux packages
# used by WSL 2 / Linux:
#   sudo apt install libimobiledevice-utils libusbmuxd-tools usbmuxd sshpass openssh-client
#
# checkra1n (iOS 12-14) and palera1n (iOS 15+) both run dropbear on port 44 with
# root's password "alpine", so one tunnel serves every supported device.
#
# Usage:
#   ./mdm.sh [-u UDID] [-n|-l] [-p PORT] [-t]
#
#   -u, --udid UDID   target one device (needed when several are connected)
#   -n, --network     device is reachable over Wi-Fi sync instead of USB
#   -l, --local       force the USB transport (default)
#   -p, --port PORT   local tunnel port (default 4444)
#   -t, --test        only verify the SSH tunnel, change nothing
#   -h, --help        show this help
set -u

cd "$(dirname "$0")" || exit 1

UDID=""
TRANSPORT=""
LOCAL_PORT=4444
SSH_PORT=44
TEST_ONLY=0
PLIST="./iFix.plist"
REMOTE_PLIST="/private/var/containers/Shared/SystemGroup/systemgroup.com.apple.configurationprofiles/Library/ConfigurationProfiles/CloudConfigurationDetails.plist"

usage() { sed -n '10,18p' "$0" | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
    case "$1" in
        -u|--udid)
            [ $# -ge 2 ] || { echo "ERROR: $1 needs a value." >&2; exit 2; }
            UDID=$2; shift 2 ;;
        -n|--network) TRANSPORT="-n"; shift ;;
        -l|--local)   TRANSPORT="-l"; shift ;;
        -p|--port)
            [ $# -ge 2 ] || { echo "ERROR: $1 needs a value." >&2; exit 2; }
            LOCAL_PORT=$2; shift 2 ;;
        -t|--test)    TEST_ONLY=1; shift ;;
        -h|--help)    usage; exit 0 ;;
        *)            echo "ERROR: unknown option '$1'" >&2; usage >&2; exit 2 ;;
    esac
done

case "$LOCAL_PORT" in
    ''|*[!0-9]*) echo "ERROR: -p must be a number." >&2; exit 2 ;;
esac

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
    echo "       Linux/WSL: sudo apt install libimobiledevice-utils libusbmuxd-tools usbmuxd sshpass openssh-client" >&2
    return 1
}

IPROXY=$(resolve iproxy) || exit 1
SSHPASS=$(resolve sshpass) || exit 1
for helper in ssh scp ssh-keygen; do
    command -v "$helper" >/dev/null 2>&1 || {
        echo "ERROR: $helper not found - install openssh-client." >&2; exit 1; }
done

if [ "$TEST_ONLY" -eq 0 ] && [ ! -f "$PLIST" ]; then
    echo "ERROR: $PLIST not found next to mdm.sh." >&2
    exit 1
fi

# Only drop the key for the local tunnel, do not wipe the user's known_hosts.
ssh-keygen -R "[localhost]:$LOCAL_PORT" >/dev/null 2>&1 || true

IPROXY_ARGS=()
[ -n "$TRANSPORT" ] && IPROXY_ARGS+=("$TRANSPORT")
[ -n "$UDID" ] && IPROXY_ARGS+=(-u "$UDID")
IPROXY_ARGS+=("$LOCAL_PORT:$SSH_PORT")

echo "Start iproxy ${TRANSPORT:-}${UDID:+ -u $UDID} ${LOCAL_PORT}:$SSH_PORT"
"$IPROXY" "${IPROXY_ARGS[@]}" >/dev/null 2>&1 &
IPROXY_PID=$!
trap 'kill "$IPROXY_PID" >/dev/null 2>&1' EXIT
sleep 2

if ! kill -0 "$IPROXY_PID" >/dev/null 2>&1; then
    echo "ERROR: iproxy could not start (port $LOCAL_PORT in use, or no device attached)." >&2
    exit 1
fi

SSH_ARGS=(-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p "$LOCAL_PORT" root@localhost)

if [ "$TEST_ONLY" -eq 1 ]; then
    echo "==> testing the SSH tunnel (nothing is written)"
    out=$("$SSHPASS" -p alpine ssh "${SSH_ARGS[@]}" 'echo TUNNEL_OK; uname -a; hostname' 2>&1)
    echo "$out"
    case "$out" in
        *TUNNEL_OK*) echo "SSH tunnel works."; exit 0 ;;
        *) echo "SSH tunnel failed - is the device jailbroken and awake?" >&2; exit 1 ;;
    esac
fi

# Rootful fakefs needs this union remount; a rootless jailbreak (the only option
# on iPadOS 16+) keeps / sealed and read-only, which is fine because the profile
# lives on the writable data volume. So a failure here is not fatal.
"$SSHPASS" -p 'alpine' ssh "${SSH_ARGS[@]}" \
    'mount -o rw,union,update / 2>/dev/null || true'

"$SSHPASS" -p alpine scp -rP "$LOCAL_PORT" -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null "$PLIST" "root@localhost:$REMOTE_PLIST" || exit 1

"$SSHPASS" -p 'alpine' ssh "${SSH_ARGS[@]}" 'launchctl reboot userspace' || exit 1

echo 'Done!'
