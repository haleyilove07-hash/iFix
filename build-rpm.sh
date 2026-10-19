#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
package_name=ifix-device-support
package_version=1.0.0
package_release=1
build_root="$project_dir/dist/rpm"
source_dir=$(mktemp -d)
trap 'rm -rf "$source_dir"' EXIT HUP INT TERM

if ! command -v rpmbuild >/dev/null 2>&1; then
  printf '%s\n' 'rpmbuild is required. Install it with: sudo dnf install rpm-build' >&2
  exit 1
fi

"$project_dir/build.sh"
mkdir -p "$source_dir/$package_name-$package_version/packaging"
cp "$project_dir/dist/iFix.pyz" "$source_dir/$package_name-$package_version/"
cp "$project_dir/icon.png" "$source_dir/$package_name-$package_version/"
cp "$project_dir/LICENSE" "$source_dir/$package_name-$package_version/"
cp "$project_dir/packaging/ifix" "$source_dir/$package_name-$package_version/packaging/"
cp "$project_dir/packaging/ifix.desktop" "$source_dir/$package_name-$package_version/packaging/"

tar -C "$source_dir" -czf "$source_dir/$package_name-$package_version.tar.gz" "$package_name-$package_version"
rm -rf "$build_root"
mkdir -p "$build_root/SOURCES" "$build_root/SPECS"
cp "$source_dir/$package_name-$package_version.tar.gz" "$build_root/SOURCES/"
cp "$project_dir/packaging/ifix.spec" "$build_root/SPECS/"

rpmbuild -ba "$build_root/SPECS/ifix.spec" \
  --define "_topdir $build_root" \
  --define "_buildhost reproducible"

printf 'Built RPM: %s\n' \
  "$build_root/RPMS/noarch/${package_name}-${package_version}-${package_release}.noarch.rpm"
