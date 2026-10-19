Name:           ifix-device-support
Version:        1.0.0
Release:        1%{?dist}
Summary:        Read-only iOS device support diagnostics

License:        GPL-3.0-or-later
URL:            https://github.com/Hackt1vator/iFix
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch

Requires:       python3
Requires:       python3-tkinter
Requires:       libimobiledevice-utils

%description
A small desktop tool that displays non-identifying iPhone and iPad device
information for support. It does not change device settings or management
enrollment.

%prep
%autosetup

%build
# The application archive is built before the RPM source archive is created.

%install
install -Dpm 0755 packaging/ifix %{buildroot}%{_bindir}/ifix
install -Dpm 0644 iFix.pyz %{buildroot}%{_libexecdir}/ifix/iFix.pyz
install -Dpm 0644 packaging/ifix.desktop %{buildroot}%{_datadir}/applications/ifix.desktop
install -Dpm 0644 icon.png %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/ifix.png
install -Dpm 0644 LICENSE %{buildroot}%{_licensedir}/%{name}/LICENSE

%files
%license %{_licensedir}/%{name}/LICENSE
%{_bindir}/ifix
%{_libexecdir}/ifix/iFix.pyz
%{_datadir}/applications/ifix.desktop
%{_datadir}/icons/hicolor/256x256/apps/ifix.png

%changelog
* Mon Oct 19 2026 iFix contributors <noreply@example.invalid> - 1.0.0-1
- Initial Fedora package
