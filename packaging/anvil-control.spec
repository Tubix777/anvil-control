Name:           anvil-control
Version:        0.9.0
Release:        1%{?dist}
Summary:        Desktop hardware monitor and power profile control
License:        MIT
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch
Requires:       python3
Requires:       python3-pyside6
Requires:       systemd
Requires:       pciutils
Requires:       polkit
Recommends:     openrgb

%description
Native Qt desktop dashboard with Linux sensor and optional NVIDIA NVML
telemetry, power profiles, hardware inventory, and local diagnostic exports.
Alpha release with board-scoped NCT6798 fan curves and optional OpenRGB controls.

%prep
%setup -q

%build

%install
mkdir -p %{buildroot}%{_datadir}/anvil-control
cp -r anvil %{buildroot}%{_datadir}/anvil-control/
find %{buildroot}%{_datadir}/anvil-control -name __pycache__ -type d -exec rm -r {} +
install -Dpm 0755 packaging/anvil-control %{buildroot}%{_bindir}/anvil-control
install -Dpm 0644 packaging/io.anvil.Control.desktop %{buildroot}%{_datadir}/applications/io.anvil.Control.desktop
install -Dpm 0644 packaging/io.anvil.Control.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/io.anvil.Control.svg
install -Dpm 0755 packaging/anvil-fan-helper %{buildroot}%{_libexecdir}/anvil-fan-helper
install -Dpm 0644 packaging/io.anvil.Control.policy %{buildroot}%{_datadir}/polkit-1/actions/io.anvil.Control.policy
install -Dpm 0644 packaging/anvil-control.conf %{buildroot}%{_prefix}/lib/modules-load.d/anvil-control.conf

%files
%license LICENSE
%doc README.md
%{_bindir}/anvil-control
%{_datadir}/anvil-control/
%{_datadir}/applications/io.anvil.Control.desktop
%{_datadir}/icons/hicolor/scalable/apps/io.anvil.Control.svg
%{_libexecdir}/anvil-fan-helper
%{_datadir}/polkit-1/actions/io.anvil.Control.policy
%{_prefix}/lib/modules-load.d/anvil-control.conf

%changelog
* Wed Sep 23 2026 Anvil contributors - 0.9.0-1
- Show the persistent theme chooser in the sidebar on every page.
- Retain admin authorization briefly for the restricted fan helper.
* Wed Sep 23 2026 Anvil contributors - 0.8.0-1
- Report detected monitoring and write capabilities across ASUS boards.
- Add Copper, Violet, Graphite and Daylight themes.
- Handle absent CPU and memory telemetry without dashboard crashes.
- Require ASUS DMI vendor as well as verified model before offering fan writes.
* Wed Sep 23 2026 Anvil contributors - 0.7.0-1
- Add persistent Anvil Yellow, Night Blue and Forest Green themes.
- Install a branded application icon for KDE taskbar and desktop launchers.
- Add safe preset fan curves on verified motherboard channels.
* Tue Sep 22 2026 Anvil contributors - 0.6.0-1
- Add read-only AMDGPU sysfs telemetry and clearer GPU fan units.
- Offer only complete verified fan channels and validate helper readback responses.
- Simplify home fan summary by listing spinning fans.
* Tue Sep 22 2026 Anvil contributors - 0.5.0-1
- Simplify navigation and combine device inventory, RGB, and diagnostics.
- Generalize DMI identification and Intel/AMD CPU temperature discovery.
- Keep write-enabled fan control limited to the physically validated board.
* Tue Sep 22 2026 Anvil contributors - 0.4.0-1
- Add NCT6798 hardware fan curves, full speed and boot-session restore.
- Add device-scoped OpenRGB color and mode controls.
* Mon Sep 21 2026 Anvil contributors - 0.3.0-1
- Animated meters, thermal alerts, selectable charts and sensor statistics.
* Mon Sep 21 2026 Anvil contributors - 0.2.0-1
- Black/yellow theme, native sans typography, motherboard diagram and home fan panel.
* Mon Sep 21 2026 Anvil contributors - 0.1.0-1
- Initial alpha with read-only telemetry and power profile controls.
