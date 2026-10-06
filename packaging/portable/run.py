#!/usr/bin/env python3
"""Run packaged source with the private Qt runtime."""
from pathlib import Path
import os
import sys

os.environ['ANVIL_MONITOR_ONLY'] = '1'
# System-wide Qt plugin paths can point at an incompatible distro Qt version.
os.environ.pop('QT_PLUGIN_PATH', None)
os.environ.pop('QT_QPA_PLATFORM_PLUGIN_PATH', None)
sys.path.insert(0, str(Path(__file__).resolve().parent / 'app'))
from anvil.launcher import main

main()
