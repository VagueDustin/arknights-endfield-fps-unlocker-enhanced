import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'tools'))
import manage
import neural


class NeuralTests(unittest.TestCase):
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
        for target, value in [('FILES', self.hashes), ('reshade_status', lambda game: True)]:
            p = patch.object(neural, target, value); p.start(); self.addCleanup(p.stop)
        p = patch.object(manage, 'game_idle', lambda: None); p.start(); self.addCleanup(p.stop)

    def install(self):
        return neural.install(self.game, self.source)

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
