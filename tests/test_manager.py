import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'tools'))
import manage


class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.game = root / 'Game with spaces'
        self.package = root / 'package'
        self.game.mkdir()
        self.package.mkdir()
        self.original = b'original game compiler'
        (self.game / manage.COMPILER).write_bytes(self.original)
        (self.package / manage.COMPILER).write_bytes(b'new proxy')
        (self.package / manage.PAYLOAD).write_bytes(b'new runtime')
        (self.package / 'package.json').write_text(json.dumps({'files': {
            name: manage.digest(self.package / name)
            for name in (manage.COMPILER, manage.PAYLOAD)}}))
        for name, replacement in [
            ('game_idle', lambda: None),
            ('inspect', lambda _: {'missing_required_exports': [],
                'runtime_sha256': 'test', 'legacy_loader_files_present': []}),
            ('pe_exports', lambda _, **kwargs: [('test_export', 1)]),
        ]:
            mock = patch.object(manage, name, replacement)
            mock.start()
            self.addCleanup(mock.stop)

    def install(self):
        return manage.install(self.game, self.package, manage.settings())

    def test_round_trip_preserves_original_and_archives_config(self):
        self.install()
        self.assertEqual((self.game / manage.ORIGINAL).read_bytes(), self.original)
        manage.configure(self.game, target=240, background=30)
        self.assertIn(b'Target=240', (self.game / manage.CONFIG).read_bytes())
        result = manage.restore(self.game)
        self.assertEqual((self.game / manage.COMPILER).read_bytes(), self.original)
        self.assertFalse((self.game / manage.PAYLOAD).exists())
        archive = self.game / result['backup_directory']
        self.assertEqual((archive / 'original.bin').read_bytes(), self.original)
        self.assertIn(b'Target=240', (archive / 'last-config.ini').read_bytes())

    def test_existing_mod_is_not_overwritten(self):
        (self.game / manage.PAYLOAD).write_bytes(b'another mod')
        with self.assertRaisesRegex(ValueError, 'conflict'):
            self.install()
        self.assertEqual((self.game / manage.COMPILER).read_bytes(), self.original)
        self.assertFalse((self.game / manage.STATE).exists())

    def test_modified_compiler_is_preserved_on_restore(self):
        self.install()
        (self.game / manage.COMPILER).write_bytes(b'game update')
        with self.assertRaisesRegex(ValueError, 'changed since'):
            manage.restore(self.game)
        self.assertEqual((self.game / manage.COMPILER).read_bytes(), b'game update')
        self.assertTrue((self.game / manage.PAYLOAD).exists())

    def test_corrupt_backup_prevents_restore(self):
        self.install()
        (self.game / manage.STATE / 'original.bin').write_bytes(b'bad')
        with self.assertRaisesRegex(ValueError, 'Backup checksum'):
            manage.restore(self.game)
        self.assertEqual((self.game / manage.COMPILER).read_bytes(), b'new proxy')

    def test_partial_install_rolls_back(self):
        write = manage.atomic_write
        failed = False
        def fail_once(path, data):
            nonlocal failed
            if path == self.game / manage.PAYLOAD and not failed:
                failed = True
                raise OSError('simulated disk failure')
            return write(path, data)
        with patch.object(manage, 'atomic_write', fail_once):
            with self.assertRaisesRegex(OSError, 'simulated'):
                self.install()
        self.assertEqual((self.game / manage.COMPILER).read_bytes(), self.original)
        self.assertFalse((self.game / manage.ORIGINAL).exists())
        self.assertFalse((self.game / manage.STATE).exists())

    def test_backup_failure_leaves_game_and_state_clean(self):
        with patch.object(manage, 'atomic_write', side_effect=OSError('no space')):
            with self.assertRaisesRegex(OSError, 'no space'):
                self.install()
        self.assertEqual((self.game / manage.COMPILER).read_bytes(), self.original)
        self.assertFalse((self.game / manage.STATE).exists())

    def test_package_tamper_prevents_install(self):
        (self.package / manage.PAYLOAD).write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            self.install()
        self.assertFalse((self.game / manage.STATE).exists())

    def test_export_mismatch_prevents_install(self):
        with patch.object(manage, 'pe_exports', lambda p, **kwargs: [p.parent.name]):
            with self.assertRaisesRegex(ValueError, 'export mismatch'):
                self.install()
        self.assertFalse((self.game / manage.STATE).exists())

    def test_missing_runtime_apis_prevent_install(self):
        with patch.object(manage, 'inspect', return_value={'missing_required_exports': ['missing']}):
            with self.assertRaisesRegex(ValueError, 'runtime APIs'):
                self.install()

    def test_invalid_settings(self):
        for arguments in ({'target': 0}, {'target': 1001}, {'background': -1}, {'vsync': 5}):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                manage.settings(**arguments)

    def test_second_install_refused(self):
        self.install()
        with self.assertRaisesRegex(ValueError, 'state exists'):
            self.install()

    def test_running_game_prevents_writes(self):
        with patch.object(manage, 'game_idle', side_effect=ValueError('Close Endfield')):
            with self.assertRaisesRegex(ValueError, 'Close Endfield'):
                self.install()
        self.assertFalse((self.game / manage.STATE).exists())


if __name__ == '__main__':
    unittest.main()
