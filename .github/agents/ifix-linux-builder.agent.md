# iFix Fedora Builder

Use this repository as a privacy-conscious, read-only iOS device support tool targeting **Fedora 44**.

## Scope

- Build and package the Python/Tkinter app for Fedora 44.
- Maintain the RPM packaging, GNOME desktop integration, dependency declarations, diagnostic reliability, and repeatable builds.
- Preserve the lightweight Python implementation where it meets the need.

## Constraints

- Keep diagnostics read-only and collect only non-identifying device details. Never include serial numbers, UDIDs, or other device identifiers in copied reports.
- Do not add or restore MDM/profile bypass, activation-lock circumvention, enrollment evasion, or jailbreak/bypass automation.
- Do not package or invoke the repository's archived macOS jailbreak, recovery, or management-bypass binaries in the supported Fedora app.
- Run device tools with argument lists, never shell-interpolated user input; set timeouts and handle missing dependencies clearly.
- Do not use `sudo`, install packages globally, or modify the host system implicitly. Declare runtime dependencies in RPM metadata and use isolated build directories. Ask before privileged system changes.
- Do not claim the GUI was tested when no display is available. State any remaining hardware or desktop-session verification gaps.

## Fedora 44 packaging

- Build with `./build-rpm.sh`; it creates an RPM beneath `dist/rpm/RPMS/noarch/`.
- Declare `python3`, `python3-tkinter`, and `libimobiledevice-utils` as runtime requirements.
- Keep the RPM architecture-independent unless native code is added.
- Use `rpmbuild` and preserve the source archive, desktop entry, icon, launcher, and license in the package.

## Validation

1. Run `python3 -m unittest discover -s tests -v`.
2. Run `sh -n build.sh build-rpm.sh`.
3. If Fedora tooling is present, run `./build-rpm.sh` and inspect the package with `rpm -qpl`.
4. Run GUI checks only when a display and a trusted iOS device are available.
