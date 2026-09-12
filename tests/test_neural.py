import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'tools'))
import manage
import neural


class NeuralTests(unittest.TestCase):
    original_graphics_api = staticmethod(neural.graphics_api)
    original_reshade_details = staticmethod(neural.reshade_details)
    original_gpu_name = staticmethod(neural.gpu_name)

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.game = Path(temp.name) / 'Game'
        self.source = Path(temp.name) / 'Imports'
        self.game.mkdir(); self.source.mkdir()
        (self.game / 'Endfield.exe').write_bytes(b'game')
        self.hashes = {}
        for name in neural.FILES:
            data = name.encode()
            (self.source / name).write_bytes(data)
            self.hashes[name] = hashlib.sha256(data).hexdigest()
        for target, value in [('FILES', self.hashes), ('reshade_status', lambda game: True),
                              ('reshade_details', lambda game: []),
                              ('graphics_api', lambda path=None: 'Unknown (test)'),
                              ('gpu_name', lambda path=None: None)]:
            p = patch.object(neural, target, value); p.start(); self.addCleanup(p.stop)
        p = patch.object(manage, 'game_idle', lambda: None); p.start(); self.addCleanup(p.stop)

    def install(self):
        return neural.install(self.game, self.source)

    def test_unsupported_gpu_blocks_install_before_writes(self):
        with patch.object(neural, 'gpu_name', lambda path=None: 'NVIDIA GeForce RTX 4090 Laptop GPU'):
            with self.assertRaisesRegex(ValueError, 'RTX 50-series'):
                self.install()
        self.assertEqual({p.name for p in self.game.iterdir()}, {'Endfield.exe'})
        with patch.object(neural, 'gpu_name', lambda path=None: 'NVIDIA GeForce RTX 5070'):
            self.install()
        self.assertTrue((self.game / neural.STATE).exists())

    def test_gpu_name_and_dlss5_capability_from_player_log(self):
        log = self.game / 'Player.log'
        log.write_text('[Vulkan init] Physical Device 000000007EB3CC90 [0]: "NVIDIA GeForce RTX 4090 Laptop GPU" deviceType=2 vendorID=10de deviceID=2757, apiVersion=1.4.351\n'
                       '[Vulkan init] Physical Device 000000007EB3CC60 [1]: "Intel(R) RaptorLake-S Mobile Graphics Controller" deviceType=1 vendorID=8086 deviceID=a788, apiVersion=1.3.271\n')
        self.assertEqual(self.original_gpu_name(log), 'NVIDIA GeForce RTX 4090 Laptop GPU')
        log.write_text('[Vulkan init] Physical Device 1 [0]: "AMD Radeon(TM) Graphics" deviceType=1 vendorID=1002 deviceID=13c0, apiVersion=1.4.315\n'
                       '[Vulkan init] Physical Device 2 [1]: "NVIDIA GeForce RTX 5070" deviceType=2 vendorID=10de deviceID=2f04, apiVersion=1.4.351\n')
        self.assertEqual(self.original_gpu_name(log), 'NVIDIA GeForce RTX 5070')
        log.write_text('Direct3D:\n    Version:  Direct3D 11.0 [level 11.1]\n    Renderer: NVIDIA GeForce RTX 3080 (ID=0x2206)\n')
        self.assertEqual(self.original_gpu_name(log), 'NVIDIA GeForce RTX 3080')
        self.assertIsNone(self.original_gpu_name(self.game / 'absent.log'))
        for name, expected in [('NVIDIA GeForce RTX 5070', True), ('NVIDIA GeForce RTX 5090 Laptop GPU', True),
                               ('NVIDIA GeForce RTX 4090 Laptop GPU', False), ('NVIDIA GeForce RTX 3080', False),
                               ('NVIDIA GeForce GTX 1080', False), ('AMD Radeon RX 7900 XTX', False),
                               ('Intel(R) Arc(TM) A770', False), ('NVIDIA GeForce RTX PRO 6000', None), (None, None)]:
            with self.subTest(name=name):
                self.assertIs(neural.dlss5_capable(name), expected)

    def test_direct3d_launch_blocks_install_before_writes(self):
        with patch.object(neural, 'graphics_api', lambda path=None: 'Direct3D 12'):
            with self.assertRaisesRegex(ValueError, 'Direct3D 12'):
                self.install()
        self.assertEqual({p.name for p in self.game.iterdir()}, {'Endfield.exe'})

    def test_graphics_api_is_read_from_player_log(self):
        log = self.game / 'Player.log'
        log.write_text('Initialize engine version: 2021.3.34f5 (0)\nGfxDevice: creating device client\n'
                       '[Vulkan init] Physical Device 0 [0]: "GPU" deviceType=2\n')
        self.assertEqual(neural.graphics_api.__wrapped__(log) if hasattr(neural.graphics_api, '__wrapped__')
                         else self.original_graphics_api(log), 'Vulkan')
        log.write_text('Direct3D:\n    Version:  Direct3D 11.0 [level 11.1]\n    Renderer: GPU\n')
        self.assertEqual(self.original_graphics_api(log), 'Direct3D 11')
        log.write_text('Initialize engine version: 2021.3.34f5 (0)\n')
        self.assertIn('Unknown', self.original_graphics_api(log))
        self.assertIn('Unknown', self.original_graphics_api(self.game / 'absent.log'))

    def test_last_launch_folder_is_read_from_the_unity_log(self):
        log = self.game / 'Player.log'
        log.write_text('[Physics::Module] Initialized MultithreadedJobDispatcher with {0} workers.\n'
                       'Initialize engine version: 2021.3.34f5 (0)\n'
                       '[Subsystems] Discovering subsystems at path C:/Program Files/GRYPHLINK/games/'
                       'Arknights Endfield/Endfield_Data/UnitySubsystems\n')
        self.assertEqual(neural.last_launch_folder(log),
                         Path(r'C:\Program Files\GRYPHLINK\games\Arknights Endfield'))
        log.write_text('Initialize engine version: 2021.3.34f5 (0)\n')
        self.assertIsNone(neural.last_launch_folder(log))
        self.assertIsNone(neural.last_launch_folder(self.game / 'absent.log'))

    def test_summary_explains_reshade_and_renderer_evidence(self):
        (self.game / 'ReShade.log').write_text(
            "12:00:00:000 [1] | INFO  | Initializing crosire's ReShade version '6.8.0.2155' (64-bit) ...\n"
            '12:00:00:001 [1] | INFO  | Registered add-on "DLSS 5 Bridge 1.4.13-pre6" v1.4.13.6 using ReShade API version 18.\n'
            '12:00:00:002 [1] | INFO  | Registered add-on "DLSS 5 Neural Rendering" v0.2026.828.517 using ReShade API version 18.\n'
            '12:00:05:000 [1] | INFO  | [DLSS 5 Neural Rendering] DLSS5 Generic: NR toggled ON via Num 0\n')
        with patch.object(neural, 'reshade_details', lambda game: ['Endfield.exe is not in the enabled list.']):
            text = neural.summary(neural.inspect(self.game))
        self.assertIn('ReShade: Setup needed', text)
        self.assertIn('not in the enabled list', text)
        self.assertIn('Add-ons loaded: DLSS 5 Bridge 1.4.13-pre6, DLSS 5 Neural Rendering', text)
        self.assertIn('switched on 1 time', text)
        self.assertIn('Last launch renderer: Unknown (test)', text)
        self.assertIn('GPU: not recorded yet - DLSS 5 support unknown', text)
        with patch.object(neural, 'gpu_name', lambda path=None: 'NVIDIA GeForce RTX 4090 Laptop GPU'):
            self.assertIn('cannot run DLSS 5', neural.summary(neural.inspect(self.game)))

    def test_reshade_details_reports_missing_registration(self):
        with tempfile.TemporaryDirectory() as programdata, patch.dict(os.environ, PROGRAMDATA=programdata):
            self.assertIn('not set up', ' '.join(self.original_reshade_details(self.game)))
            root = Path(programdata) / 'ReShade'; root.mkdir()
            (root / 'ReShadeApps.ini').write_text('Apps=C:\\Other\\Game.exe\n', encoding='utf-8-sig')
            problems = self.original_reshade_details(self.game)
            self.assertTrue(any('enabled application list' in p for p in problems))
            self.assertTrue(any('missing from ProgramData' in p for p in problems))

    def test_roundtrip_preserves_original_settings_and_native_dll(self):
        original = b'; keep comment\r\n[INPUT]\r\nKeyOverlay=36,0,0,0\r\n'
        (self.game / neural.CONFIG).write_bytes(original)
        (self.game / 'nvngx_dlss.dll').write_bytes(b'original')
        self.install()
        data = (self.game / neural.CONFIG).read_bytes()
        self.assertIn(b'NRToggleKey=45', data)
        self.assertIn(b'NeuralUplift=0', data)
        neural.restore(self.game)
        self.assertEqual((self.game / neural.CONFIG).read_bytes(), original)
        self.assertEqual((self.game / 'nvngx_dlss.dll').read_bytes(), b'original')
        self.assertFalse((self.game / neural.STATE).exists())
        self.assertFalse((self.game / 'nvngx_dlssnr.dll').exists())

    def test_existing_user_key_and_enabled_state_preserved(self):
        data = b'[RenoDX.DLSS5]\nNRToggleKey=44\nNeuralUplift=1\n'
        (self.game / neural.CONFIG).write_bytes(data)
        self.install()
        self.assertEqual((self.game / neural.CONFIG).read_bytes(), data)

    def test_external_install_not_adopted_or_overwritten(self):
        path = self.game / 'nvngx_dlssnr.dll'; path.write_bytes(b'external')
        with self.assertRaisesRegex(ValueError, 'Existing file preserved'):
            self.install()
        self.assertEqual(path.read_bytes(), b'external')
        self.assertFalse((self.game / neural.STATE).exists())

    def test_external_removal_is_a_read_only_noop_even_while_running(self):
        path = self.game / 'nvngx_dlssnr.dll'
        path.write_bytes(b'external')
        with patch.object(manage, 'game_idle', side_effect=AssertionError('Should not require idle for a no-op')):
            result = neural.restore(self.game)
        self.assertIn('Nothing to remove', result['message'])
        self.assertEqual(path.read_bytes(), b'external')
        self.assertFalse((self.game / neural.STATE).exists())

    def test_missing_recovery_record_has_actionable_message(self):
        with self.assertRaisesRegex(ValueError, 'installed outside Fate Engine'):
            neural.read_state(self.game)

    def test_unrecognized_download_rejected_before_writes(self):
        (self.source / 'nvngx_dlssnr.dll').write_bytes(b'wrong')
        with self.assertRaisesRegex(ValueError, 'Not the tested'):
            self.install()
        self.assertEqual(len(list(self.game.iterdir())), 1)

    def test_reshade_prerequisite_blocks_before_writes(self):
        with patch.object(neural, 'reshade_status', return_value=False):
            with self.assertRaisesRegex(ValueError, 'ReShade'):
                self.install()
        self.assertFalse((self.game / neural.STATE).exists())

    def test_running_game_blocks_mutations(self):
        with patch.object(manage, 'game_idle', side_effect=ValueError('Close Endfield')):
            with self.assertRaisesRegex(ValueError, 'Close Endfield'):
                self.install()

    def test_failure_after_first_copy_recovers(self):
        original = manage.atomic_write
        def fail(path, data):
            if path.name == 'dlss5-bridge.addon64':
                raise OSError('simulated disk failure')
            original(path, data)
        with patch.object(manage, 'atomic_write', side_effect=fail):
            with self.assertRaisesRegex(OSError, 'simulated'):
                self.install()
        self.assertFalse((self.game / neural.STATE).exists())
        for name in neural.OWNED:
            self.assertFalse((self.game / name).exists())

    def test_changed_dll_blocks_removal_before_any_deletion(self):
        self.install()
        (self.game / 'nvngx_dlssnr.dll').write_bytes(b'updated externally')
        with self.assertRaisesRegex(ValueError, 'Changed file'):
            neural.restore(self.game)
        self.assertTrue(all((self.game / name).exists() for name in neural.FILES))

    def test_settings_changed_by_game_preserved_on_removal(self):
        self.install()
        (self.game / neural.CONFIG).write_bytes(b'[User]\nNewSetting=1\n')
        result = neural.restore(self.game)
        self.assertEqual(result['preserved_user_settings'], [neural.CONFIG])
        self.assertIn(b'NewSetting=1', (self.game / neural.CONFIG).read_bytes())

    def test_configure_preserves_unrelated_settings_and_backs_up(self):
        self.install()
        result = neural.configure(self.game, enabled=True, insert=True)
        self.assertTrue((self.game / result['backup']).exists())
        self.assertIn(b'NeuralUplift=1', (self.game / neural.CONFIG).read_bytes())
        self.assertEqual(neural.inspect(self.game)['saved_enabled'], '1')

    def test_invalid_recovery_paths_rejected(self):
        self.install()
        path = self.game / neural.STATE
        state = json.loads(path.read_text())
        state['files']['../outside'] = state['files'].pop(neural.CONFIG)
        path.write_text(json.dumps(state))
        with self.assertRaisesRegex(ValueError, 'file list'):
            neural.restore(self.game)

    def test_merge_keeps_sections_and_bom(self):
        data = b'\xef\xbb\xbf[RenoDX.DLSS5]\r\nNeuralUplift=0\r\n[Other]\r\nKey=3\r\n'
        merged = neural.merge_settings(data, {'NRToggleKey': 45})
        self.assertTrue(merged.startswith(b'\xef\xbb\xbf'))
        self.assertIn(b'NRToggleKey=45\r\n[Other]\r\nKey=3', merged)

    def test_app_uninstall_restores_recorded_neural_install(self):
        import desktop_state
        self.install()
        record = self.game.parent / 'desktop.json'
        record.write_text(json.dumps({'games': [str(self.game)]}))
        with patch.object(desktop_state, 'location', return_value=record):
            result = desktop_state.restore_recorded()
        self.assertIn(str(self.game) + ' (DLSS)', result['restored'])
        self.assertFalse((self.game / neural.STATE).exists())

    def test_interrupted_journal_blocks_settings_but_allows_restore(self):
        self.install()
        path = self.game / neural.STATE
        data = json.loads(path.read_text()); data['phase'] = 'installing'
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'interrupted'):
            neural.configure(self.game, enabled=True)
        neural.restore(self.game)
        self.assertFalse(path.exists())

    def test_corrupt_config_backup_blocks_restore(self):
        (self.game / neural.CONFIG).write_bytes(b'[INPUT]\nKeyOverlay=36\n')
        self.install()
        path = self.game / neural.STATE
        data = json.loads(path.read_text()); data['files'][neural.CONFIG]['before_hash'] = '0' * 64
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'checksum'):
            neural.restore(self.game)
        self.assertTrue((self.game / 'nvngx_dlssnr.dll').exists())


if __name__ == '__main__':
    unittest.main()
