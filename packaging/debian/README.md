# Debian-family packages

The default release DEB embeds the verified Qt wheels and application source from
the portable Linux archive. It installs normal system GUI dependencies through
apt, then creates a private runtime as your normal desktop user on first launch.
It never downloads code during installation or modifies system Python with pip.
Use `sudo apt install ./anvil-control_<version>.alpha1-1_amd64.deb` so apt resolves
the dependency list. Start Anvil Control from your application menu afterwards.
Download filenames use `.alpha1-1`; the package's internal Debian version retains
`~alpha1-1` so its prerelease version metadata remains unchanged.

This package requires amd64, glibc 2.34 or newer, Python 3.10–3.14 and python3-venv.
It does not depend on the distribution providing PySide6, so Ubuntu 22.04/24.04
can use it. Zorin and Deepin remain separately testable targets; Ubuntu startup
tests do not prove derivative distribution or physical motherboard compatibility.
Every DEB starts in monitoring-only mode and includes no privileged fan helper,
polkit action, maintainer scripts or kernel module configuration.

## Build

Build the portable archive first, then embed it in the DEB:

```sh
python3 packaging/portable/build_bundle.py --wheel-directory /tmp/anvil-wheels
python3 packaging/debian/build_deb.py --bundle anvil-control-<version>-linux-x86_64.tar.gz
```

Both builders use Python's standard library. Only the portable builder contacts
PyPI to obtain the two hash-pinned wheels and Qt's download server to obtain the
matching hash-pinned source archive for license notices when not cached. Set
`SOURCE_DATE_EPOCH` to a nonnegative timestamp for deterministic output (default
0). `--output` selects a new file; existing output files are never overwritten.

For distributions with native Qt bindings, a smaller architecture-independent
variant is available:

```sh
python3 packaging/debian/build_deb.py --system-qt
```

This variant depends on `python3-pyside6.qtwidgets`, available in the tested Debian
13 and Ubuntu 26.04 repositories. It is not usable from Ubuntu 24.04's standard
repositories; use the bundled amd64 DEB there. Install only one variant at a time.
Inspect a DEB using `dpkg-deb --info` and `dpkg-deb --contents` on a Debian-family
system. Release notes identify the versions actually installation/startup tested.
