"""Portable entry points cannot accidentally enable system setting writes."""
import os
import runpy
import unittest
from unittest.mock import patch

from anvil.launcher import main


class LauncherTests(unittest.TestCase):
    def test_portable_entry_overrides_user_environment_before_app_starts(self):
        with patch.dict(os.environ, {'ANVIL_MONITOR_ONLY': '0'}):
            with patch('anvil.app.main', side_effect=lambda: os.environ.get('ANVIL_MONITOR_ONLY')) as run:
                self.assertEqual(main(), '1')
            run.assert_called_once_with()

    def test_python_module_entry_forces_monitor_only_even_with_disabled_flag(self):
        for value in (None, '0'):
            with self.subTest(initial_flag=value), patch.dict(os.environ):
                if value is None:
                    os.environ.pop('ANVIL_MONITOR_ONLY', None)
                else:
                    os.environ['ANVIL_MONITOR_ONLY'] = value
                with patch('anvil.app.main', side_effect=lambda: os.environ.get('ANVIL_MONITOR_ONLY')) as run:
                    runpy.run_module('anvil', run_name='__main__')
                run.assert_called_once_with()
                self.assertEqual(os.environ.get('ANVIL_MONITOR_ONLY'), '1')
