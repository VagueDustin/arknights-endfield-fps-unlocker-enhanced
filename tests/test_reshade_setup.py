import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'tools'))
import reshade_setup

class SetupTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.setup = self.root / 'prerequisites' / reshade_setup.SETUP_NAME
        self.setup.parent.mkdir()
        for target, value in [('package_root', lambda: self.root),
                              ('neural.game_path', lambda game: Path(game)),
                              ('manage.game_idle', lambda: None)]:
            mock = patch('reshade_setup.' + target, value); mock.start(); self.addCleanup(mock.stop)

    def test_verified_setup_targets_vulkan_without_shell(self):
        self.setup.write_bytes(b'fixture')
        with patch.object(reshade_setup, 'SETUP_HASH', hashlib.sha256(b'fixture').hexdigest()), patch('reshade_setup.subprocess.Popen') as launch:
            reshade_setup.launch(self.root)
            self.assertEqual(launch.call_args.args[0], [str(self.setup), str(self.root / 'Endfield.exe'), '--api', 'vulkan'])
            self.assertNotIn('shell', launch.call_args.kwargs)

    def test_modified_setup_never_launches(self):
        self.setup.write_bytes(b'unrecognized')
        with patch('reshade_setup.subprocess.Popen') as launch:
            with self.assertRaisesRegex(ValueError, 'failed verification'):
                reshade_setup.launch(self.root)
            launch.assert_not_called()

    def test_public_package_opens_official_download(self):
        with patch('reshade_setup.webbrowser.open') as browse, patch('reshade_setup.subprocess.Popen') as launch:
            reshade_setup.launch(self.root)
            browse.assert_called_once_with('https://reshade.me/#download')
            launch.assert_not_called()
