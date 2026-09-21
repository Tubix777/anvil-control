Name:           anvil-control
Version:        0.2.0
Release:        1%{?dist}
Summary:        Desktop hardware monitor and power profile control
License:        MIT
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch
Requires:       python3
Requires:       python3-pyside6
Requires:       systemd
Requires:       pciutils

%description
Native Qt desktop dashboard with Linux sensor and optional NVIDIA NVML
telemetry, power profiles, hardware inventory, and local diagnostic exports.
Alpha release: fan and RGB writes are not implemented.

%prep
%setup -q

%build

%install
mkdir -p %{buildroot}%{_datadir}/anvil-control
cp -r anvil %{buildroot}%{_datadir}/anvil-control/
find %{buildroot}%{_datadir}/anvil-control -name __pycache__ -type d -exec rm -r {} +
install -Dpm 0755 packaging/anvil-control %{buildroot}%{_bindir}/anvil-control
install -Dpm 0644 packaging/io.anvil.Control.desktop %{buildroot}%{_datadir}/applications/io.anvil.Control.desktop

%files
%license LICENSE
%doc README.md
%{_bindir}/anvil-control
%{_datadir}/anvil-control/
%{_datadir}/applications/io.anvil.Control.desktop

%changelog
* Mon Sep 21 2026 Anvil contributors - 0.2.0-1
- Black/yellow theme, native sans typography, motherboard diagram and home fan panel.
* Mon Sep 21 2026 Anvil contributors - 0.1.0-1
- Initial alpha with read-only telemetry and power profile controls.
