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
                              ('neural.graphics_api', lambda path=None: 'Unknown (test)'),
                              ('neural.gpu_name', lambda path=None: None),
                              ('neural.reshade_status', lambda game: False),
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

    def test_direct3d_game_does_not_start_the_vulkan_wizard(self):
        self.setup.write_bytes(b'fixture')
        with patch('reshade_setup.neural.graphics_api', lambda path=None: 'Direct3D 12'), \
             patch('reshade_setup.subprocess.Popen') as launch, patch('reshade_setup.webbrowser.open') as browse:
            with self.assertRaisesRegex(ValueError, 'Direct3D 12'):
                reshade_setup.launch(self.root)
            launch.assert_not_called(); browse.assert_not_called()

    def test_unsupported_gpu_does_not_start_the_wizard(self):
        self.setup.write_bytes(b'fixture')
        with patch('reshade_setup.neural.gpu_name', lambda path=None: 'NVIDIA GeForce RTX 4090 Laptop GPU'), \
             patch('reshade_setup.subprocess.Popen') as launch:
            with self.assertRaisesRegex(ValueError, 'RTX 50-series'):
                reshade_setup.launch(self.root)
            launch.assert_not_called()

    def test_registered_game_is_not_offered_the_wizard_again(self):
        self.setup.write_bytes(b'fixture')
        with patch('reshade_setup.neural.reshade_status', lambda game: True), patch('reshade_setup.subprocess.Popen') as launch:
            message = reshade_setup.launch(self.root)
            self.assertIn('already registered', message)
            launch.assert_not_called()
