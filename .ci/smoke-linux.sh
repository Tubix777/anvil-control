#!/bin/sh
# Run only in a disposable container; packages install into that container.
set -eu
if [ ! -f /.dockerenv ] && [ ! -f /run/.containerenv ]; then
    printf 'This test must run inside a disposable container.\n' >&2
    exit 2
fi
mode=$1
version=$2
artifacts=$3
case "$mode" in bundled|system|portable) ;; *) exit 2 ;; esac
case "$version" in ''|*[!0-9.]*) exit 2 ;; esac

if command -v apt-get >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq --no-install-recommends python3 python3-venv \
        libgl1 libegl1 libopengl0 libglib2.0-0 libfontconfig1 libdbus-1-3 \
        libxkbcommon0 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 \
        libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-xinerama0 \
        libxcb-xkb1 libxcb-shape0 libxcb-sync1 libxcb-xfixes0 libxcb-randr0 \
        libx11-xcb1 libwayland-client0 libwayland-cursor0 \
        libwayland-egl1 fonts-dejavu-core xvfb xauth
elif command -v dnf >/dev/null 2>&1; then
    dnf install -y -q python3 python3-pip mesa-libGL mesa-libEGL libglvnd-opengl \
        glib2 fontconfig dbus-libs libxkbcommon libxkbcommon-x11 libxcb \
        xcb-util-cursor xcb-util-wm xcb-util-image xcb-util-keysyms \
        xcb-util-renderutil libX11 dejavu-sans-fonts xorg-x11-server-Xvfb xorg-x11-xauth
elif command -v pacman >/dev/null 2>&1; then
    pacman -Syu --noconfirm --needed python python-pip libglvnd glib2 fontconfig \
        dbus libxkbcommon libxkbcommon-x11 libxcb xcb-util-cursor xcb-util-wm \
        xcb-util-image xcb-util-keysyms xcb-util-renderutil libx11 \
        ttf-dejavu xorg-server-xvfb xorg-xauth
else
    printf 'No supported container package manager\n' >&2
    exit 2
fi

useradd --create-home --uid 2000 anvilci
if [ "$mode" = bundled ]; then
    apt-get install -y -qq "$artifacts/anvil-control_${version}.alpha1-1_amd64.deb"
    app=/usr/share/anvil-control/portable/app
    runuser -u anvilci -- python3 /usr/share/anvil-control/portable/install.py
elif [ "$mode" = system ]; then
    apt-get install -y -qq "$artifacts/anvil-control_${version}.alpha1-1_all.deb"
    # QtTest is a smoke-test dependency, separate from the application's QtWidgets.
    apt-get install -y -qq --no-install-recommends python3-pyside6.qttest
    app=/usr/share/anvil-control
else
    tar -xzf "$artifacts/anvil-control-${version}-linux-x86_64.tar.gz" -C /home/anvilci
    app="/home/anvilci/anvil-control-${version}-linux-x86_64/app"
    chown -R anvilci:anvilci "/home/anvilci/anvil-control-${version}-linux-x86_64"
    runuser -u anvilci -- python3 "/home/anvilci/anvil-control-${version}-linux-x86_64/install.py"
fi
if [ "$mode" = system ]; then
    interpreter=/usr/bin/python3
else
    minor=$(python3 -c 'import sys; print(str(sys.version_info[0])+"."+str(sys.version_info[1]))')
    interpreter="/home/anvilci/.local/share/anvil-control/runtime/${version}-py${minor}/venv/bin/python"
fi
runuser -u anvilci -- env QT_QPA_PLATFORM=offscreen PYTHONPATH="$app" \
    "$interpreter" tests/smoke_portable.py
# Also exercise the actual X11 plugin and native libraries under a virtual display.
runuser -u anvilci -- env QT_QPA_PLATFORM=xcb PYTHONPATH="$app" \
    xvfb-run -a "$interpreter" tests/smoke_portable.py
