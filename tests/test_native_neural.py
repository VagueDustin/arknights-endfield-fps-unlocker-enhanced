import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import native_neural

class NativeInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        # GitHub's Windows runner may use a short-name TEMP path. Match the
        # production path normalization before assigning mock runtime versions.
        self.root=Path(self.temp.name).resolve();self.game=self.root/'game';self.source=self.root/'source'
        self.game.mkdir();self.source.mkdir();(self.game/'Endfield.exe').write_bytes(b'game')
        hashes={}
        for name in native_neural.FILES:
            data=name.encode();(self.source/name).write_bytes(data);hashes[name]=hashlib.sha256(data).hexdigest()
        (self.source/'manifest.json').write_text(json.dumps({'files':hashes}))
        for name,value in [('manage.game_idle',None),('neural.reshade_status',False)]:
            mock=patch('native_neural.'+name,return_value=value);mock.start();self.addCleanup(mock.stop)
    def test_round_trip(self):
        native_neural.install(self.game,self.source)
        native_neural.restore(self.game)
        self.assertEqual({p.name for p in self.game.iterdir()},{'Endfield.exe'})
    def test_existing_file_preserved(self):
        (self.game/'winmm.dll').write_bytes(b'external')
        with self.assertRaises(ValueError):native_neural.install(self.game,self.source)
        self.assertEqual((self.game/'winmm.dll').read_bytes(),b'external')
    def test_changed_file_blocks_entire_removal(self):
        native_neural.install(self.game,self.source)
        (self.game/'OptiScaler.ini').write_bytes(b'changed')
        with self.assertRaises(ValueError):native_neural.restore(self.game)
        self.assertTrue(all((self.game/name).exists() for name in native_neural.FILES))
    def test_bad_package_no_writes(self):
        (self.source/'nvngx_dlssnr.dll').write_bytes(b'bad')
        with self.assertRaises(ValueError):native_neural.install(self.game,self.source)
        self.assertEqual({p.name for p in self.game.iterdir()},{'Endfield.exe'})
    def test_partial_install_rolls_back(self):
        original=native_neural.manage.atomic_write
        def fail(path,data):
            if path.name=='nvngx_dlssnr.dll':raise OSError('simulated copy failure')
            return original(path,data)
        with patch('native_neural.manage.atomic_write',side_effect=fail):
            with self.assertRaises(OSError):native_neural.install(self.game,self.source)
        self.assertEqual({p.name for p in self.game.iterdir()},{'Endfield.exe'})
    def test_older_runtime_backed_up_and_restored(self):
        runtime=self.game/'msvcp140.dll';runtime.write_bytes(b'original older runtime')
        with patch('native_neural.file_version',side_effect=lambda p:(14,29,0,0) if p.parent==self.game else (14,44,0,0)):
            native_neural.install(self.game,self.source)
        self.assertEqual(runtime.read_bytes(),b'msvcp140.dll')
        native_neural.restore(self.game)
        self.assertEqual(runtime.read_bytes(),b'original older runtime')
    def test_newer_runtime_not_owned_or_removed(self):
        runtime=self.game/'msvcp140.dll';runtime.write_bytes(b'newer runtime')
        with patch('native_neural.file_version',side_effect=lambda p:(14,50,0,0) if p.parent==self.game else (14,44,0,0)):
            native_neural.install(self.game,self.source)
        self.assertEqual(runtime.read_bytes(),b'newer runtime')
        native_neural.restore(self.game)
        self.assertEqual(runtime.read_bytes(),b'newer runtime')
    def test_identical_runtime_preserved(self):
        runtime=self.game/'msvcp140.dll';runtime.write_bytes(b'msvcp140.dll')
        native_neural.install(self.game,self.source)
        native_neural.restore(self.game)
        self.assertTrue(runtime.exists())
    def test_backup_corruption_blocks_removal(self):
        runtime=self.game/'msvcp140.dll';runtime.write_bytes(b'older')
        with patch('native_neural.file_version',side_effect=lambda p:(14,29,0,0) if p.parent==self.game else (14,44,0,0)):
            native_neural.install(self.game,self.source)
        journal=self.game/native_neural.STATE
        record=json.loads(journal.read_text());record['before']['msvcp140.dll']['sha256']='bad'
        journal.write_text(json.dumps(record))
        with self.assertRaises(ValueError):native_neural.restore(self.game)
        self.assertTrue((self.game/'winmm.dll').exists())

if __name__=='__main__':unittest.main()
