import unittest
from pathlib import Path
from xml.etree import ElementTree


POLICY = Path(__file__).resolve().parents[1] / 'packaging' / 'io.anvil.Control.policy'


class PolicyTests(unittest.TestCase):
    def test_passwordless_fan_authorization_is_active_session_and_helper_scoped(self):
        root = ElementTree.parse(POLICY).getroot()
        actions = root.findall('action')
        self.assertEqual(len(actions), 1)
        action = actions[0]
        self.assertEqual(action.attrib['id'], 'io.anvil.Control.fan-control')
        self.assertEqual(action.findtext('defaults/allow_any'), 'no')
        self.assertEqual(action.findtext('defaults/allow_inactive'), 'no')
        self.assertEqual(action.findtext('defaults/allow_active'), 'yes')
        annotations = {node.attrib['key']:node.text for node in action.findall('annotate')}
        self.assertEqual(annotations, {
            'org.freedesktop.policykit.exec.path':'/usr/libexec/anvil-fan-helper'})


if __name__ == '__main__':
    unittest.main()
