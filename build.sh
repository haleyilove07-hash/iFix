#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
build_dir=$(mktemp -d)
trap 'rm -rf "$build_dir"' EXIT HUP INT TERM
source_date_epoch=${SOURCE_DATE_EPOCH:-$(git -C "$project_dir" log -1 --format=%ct 2>/dev/null || true)}
if [ -z "$source_date_epoch" ]; then
  source_date_epoch=$(python3 -c 'import os, sys; print(int(os.stat(sys.argv[1]).st_mtime))' "$project_dir/iFix.py")
fi
case $source_date_epoch in
  *[!0-9]*|'')
    printf '%s\n' 'SOURCE_DATE_EPOCH must be a non-negative integer.' >&2
    exit 1
    ;;
esac
if [ "$source_date_epoch" -lt 315532800 ]; then
  printf '%s\n' 'SOURCE_DATE_EPOCH must not be earlier than 1980-01-01 for ZIP output.' >&2
  exit 1
fi
export SOURCE_DATE_EPOCH="$source_date_epoch"

mkdir -p "$project_dir/dist"
cp "$project_dir/iFix.py" "$build_dir/__main__.py"
python3 - "$build_dir/__main__.py" "$SOURCE_DATE_EPOCH" <<'PY'
import os
import sys

path, timestamp = sys.argv[1], int(sys.argv[2])
os.utime(path, (timestamp, timestamp))
PY
python3 -m zipapp "$build_dir" \
  --output "$project_dir/dist/iFix.pyz" \
  --python '/usr/bin/env python3'
chmod +x "$project_dir/dist/iFix.pyz"
