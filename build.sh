#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
build_dir=$(mktemp -d)
trap 'rm -r "$build_dir"' EXIT
source_date_epoch=${SOURCE_DATE_EPOCH:-$(git -C "$project_dir" log -1 --format=%ct 2>/dev/null || true)}
if [ -z "$source_date_epoch" ]; then
  source_date_epoch=$(python3 -c 'import os, sys; print(int(os.stat(sys.argv[1]).st_mtime))' "$project_dir/iFix.py")
fi
export SOURCE_DATE_EPOCH="$source_date_epoch"

mkdir -p "$project_dir/dist"
cp "$project_dir/iFix.py" "$build_dir/__main__.py"
touch -d "@$SOURCE_DATE_EPOCH" "$build_dir/__main__.py"
python3 -m zipapp "$build_dir" \
  --output "$project_dir/dist/iFix.pyz" \
  --python '/usr/bin/env python3'
chmod +x "$project_dir/dist/iFix.pyz"