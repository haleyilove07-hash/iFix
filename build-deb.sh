#!/bin/sh
set -eu
umask 022

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
package_version=1.0.0-1
build_dir=$(mktemp -d)
trap 'rm -r "$build_dir"' EXIT
source_date_epoch=${SOURCE_DATE_EPOCH:-$(git -C "$project_dir" log -1 --format=%ct 2>/dev/null || true)}
if [ -z "$source_date_epoch" ]; then
  source_date_epoch=$(python3 -c 'import os, sys; print(int(os.stat(sys.argv[1]).st_mtime))' "$project_dir/iFix.py")
fi
export SOURCE_DATE_EPOCH="$source_date_epoch"

"$project_dir/build.sh"

package_dir="$build_dir/package"
install -D -m 644 "$project_dir/dist/iFix.pyz" "$package_dir/usr/lib/ifix/iFix.pyz"
install -D -m 755 "$project_dir/packaging/ifix" "$package_dir/usr/bin/ifix"
install -D -m 644 "$project_dir/packaging/ifix.desktop" \
  "$package_dir/usr/share/applications/ifix.desktop"
install -D -m 644 "$project_dir/icon.png" "$package_dir/usr/share/pixmaps/ifix.png"
install -D -m 644 "$project_dir/LICENSE" \
  "$package_dir/usr/share/doc/ifix-device-support/copyright"
install -D -m 644 "$project_dir/packaging/control" "$package_dir/DEBIAN/control"
find "$package_dir" -type d -exec chmod 755 {} +
find "$package_dir" -exec touch -h -d "@$SOURCE_DATE_EPOCH" {} +

mkdir -p "$project_dir/dist"
dpkg-deb --build --root-owner-group "$package_dir" \
  "$project_dir/dist/ifix_${package_version}_all.deb"