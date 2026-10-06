# Qt runtime and source code

This archive redistributes the unmodified PySide6-Essentials and shiboken6
6.11.2 wheels from PyPI. SHA256SUMS and requirements.txt identify their exact
contents. The upstream wheels omit separate license files; this archive therefore
includes the license texts from the matching hash-verified Qt for Python source
release under `licenses/QtForPython/`. Qt for Python
is offered under LGPLv3/GPLv3 or a commercial license; see those notices for the
licenses applying to each component. The source archives below also retain their
third-party notices and component-specific license information. Anvil Control
itself is MIT licensed.

Corresponding upstream source can be downloaded freely from these locations:

- [Qt for Python 6.11.2 source](https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.11.2-src/pyside-setup-everywhere-src-6.11.2.tar.xz)
- [Qt 6.11.2 source archives](https://download.qt.io/official_releases/qt/6.11/6.11.2/single/)
- [Qt build instructions](https://doc.qt.io/qt-6/linux-building.html)
- [Qt for Python build instructions](https://doc.qt.io/qtforpython-6/building_from_source/index.html)
- [PySide6-Essentials release](https://pypi.org/project/PySide6-Essentials/6.11.2/)
- [shiboken6 release](https://pypi.org/project/shiboken6/6.11.2/)

The source archive used for the included license notices has SHA256
`cba47efbaad1bedd529725cbc14e21f156c7a19366f07b3edfbb076ffd7afdf8`.

You may replace the Qt runtime in the private venv with your modified compatible
build; no application signature check prevents loading a modified installed Qt
runtime. Bundle checksums verify the shipped installer inputs, not your private
runtime after installation. Your distribution's GUI/system libraries have their
own licenses and are not copied into this archive.
