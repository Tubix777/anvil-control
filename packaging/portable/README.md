# Anvil Control for Linux

Extract the archive, open its folder, and run `./anvil-control`. The first launch
creates a private Qt runtime under `~/.local/share/anvil-control/runtime/` using
the included wheels. It needs no network, root access or system-wide pip install.
Launch it as your normal desktop user. To add it to the application menu:

```sh
python3 install.py --desktop
```

Keep the extracted folder in place while using that menu entry. Remove the
`~/.local/share/applications/io.anvil.Control.Portable.desktop` file to remove the
menu entry. The runtime directory belongs only to Anvil and may be removed after
closing Anvil; it will be recreated on the next launch. Configuration and readings
are not bundled with releases.

## Requirements

Linux x86_64, glibc 2.34 or newer, Python 3.10–3.14 with `venv`/`ensurepip`, and a
working desktop session are required. Run `python3 install.py --check` to verify
the archive and base runtime. ARM, Alpine/musl and older glibc are not supported
by this archive. Native distribution packages may support other architectures.

On Debian/Ubuntu, install the GUI libraries and venv support if missing:

```sh
sudo apt install python3-venv libgl1 libegl1 libopengl0 libglib2.0-0 libfontconfig1 libdbus-1-3 libxkbcommon0 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-xinerama0 libxcb-xkb1 libxcb-shape0 libxcb-sync1 libxcb-xfixes0 libxcb-randr0 libx11-xcb1
```

On releases that renamed GLib to `libglib2.0-0t64`, apt resolves the old name to
the matching package. Use your own distribution's package manager for equivalent
libraries; the installer reports a missing-library error and never installs
system packages itself. X11 uses Qt's xcb plugin; Wayland uses Qt's included
Wayland plugin and also needs the distribution's Wayland/EGL runtime libraries.

## Monitoring and hardware controls

This distribution build always starts in monitoring-only mode. Sensor and fan
readings depend on what your kernel exposes. Fan curves, power profiles and RGB
writes are disabled; the archive includes no privileged helper, polkit action or
kernel module configuration. Starting the app on another distribution does not
prove that a particular motherboard supports hardware writes.

Ubuntu, Debian, Zorin and Deepin are distinct test targets. A successful Ubuntu
test does not establish Zorin or Deepin support. Consult the release support
matrix for the versions actually tested. Container GUI launch tests validate
dependencies and startup, not physical sensor availability or fan controls.

See THIRD_PARTY.md for the bundled Qt licenses and corresponding source links.
