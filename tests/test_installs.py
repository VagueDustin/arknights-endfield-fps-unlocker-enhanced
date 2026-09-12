"""Two Endfield installations on one PC is the failure that mimics a broken setup."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import installs


class InstallDiscoveryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.epic = self.root / 'Epic Games' / 'ArknightsEndfieldgowoU'
        self.official = self.root / 'GRYPHLINK'
        for folder in (self.epic / 'games' / 'EndField Game', self.official / 'games' / 'Arknights Endfield'):
            folder.mkdir(parents=True)
            (folder / installs.EXE).write_bytes(b'game')
        self.manifests = self.root / 'Epic' / 'EpicGamesLauncher' / 'Data' / 'Manifests'
        self.manifests.mkdir(parents=True)
        (self.manifests / 'a.item').write_text(json.dumps(
            {'DisplayName': 'Arknights: Endfield', 'InstallLocation': str(self.epic)}), encoding='utf-8')
        (self.manifests / 'b.item').write_text(json.dumps(
            {'DisplayName': 'Some Other Game', 'InstallLocation': str(self.root / 'other')}), encoding='utf-8')
        patcher = patch.dict(os.environ, PROGRAMDATA=str(self.root))
        patcher.start()
        self.addCleanup(patcher.stop)

    def uninstall(self):
        return iter([('GRYPHLINK', str(self.official)),
                     ('Microsoft Edge', str(self.root / 'edge')),
                     ('Broken Entry', '')])

    def test_epic_manifest_is_matched_by_display_name(self):
        self.assertEqual(list(installs.epic_entries()), [('Epic Games', str(self.epic))])

    def test_launcher_entries_ignore_unrelated_software(self):
        with patch.object(installs, 'uninstall_entries', self.uninstall):
            self.assertEqual(list(installs.launcher_entries()), [('GRYPHLINK', str(self.official))])

    def test_game_folders_finds_the_exe_under_a_launcher_games_folder(self):
        self.assertEqual([str(p) for p in installs.game_folders(self.official)],
                         [str(self.official / 'games' / 'Arknights Endfield')])
        # An install that keeps Endfield.exe in its root is found too.
        plain = self.root / 'Portable'
        plain.mkdir()
        (plain / installs.EXE).write_bytes(b'game')
        self.assertEqual([str(p) for p in installs.game_folders(plain)], [str(plain)])
        self.assertEqual(list(installs.game_folders(self.root / 'absent')), [])

    def test_find_games_returns_both_installations_once_each(self):
        with patch.object(installs, 'uninstall_entries', self.uninstall):
            found = installs.find_games()
        self.assertEqual(found, [('Epic Games', str(self.epic / 'games' / 'EndField Game')),
                                 ('GRYPHLINK', str(self.official / 'games' / 'Arknights Endfield'))])

    def test_find_game_prefers_the_install_the_game_actually_ran(self):
        played = self.official / 'games' / 'Arknights Endfield'
        with patch.object(installs, 'uninstall_entries', self.uninstall):
            with patch.object(installs, 'last_launched', lambda: played):
                self.assertEqual(installs.find_game(), str(played))
            # With no evidence of a launch, discovery order stands.
            with patch.object(installs, 'last_launched', lambda: None):
                self.assertEqual(installs.find_game(), str(self.epic / 'games' / 'EndField Game'))
            # A recorded launch from somewhere unknown never invents a selection.
            with patch.object(installs, 'last_launched', lambda: self.root / 'elsewhere'):
                self.assertEqual(installs.find_game(), str(self.epic / 'games' / 'EndField Game'))

    def test_find_game_is_empty_when_nothing_is_installed(self):
        with patch.object(installs, 'epic_entries', lambda: iter(())), \
             patch.object(installs, 'uninstall_entries', lambda: iter(())):
            self.assertEqual(installs.find_game(), '')

    def test_same_folder_normalizes_case_and_separators(self):
        self.assertTrue(installs.same_folder('C:\\Games\\EndField', 'c:/games/endfield'))
        self.assertFalse(installs.same_folder('C:\\Games\\EndField', 'C:\\Games\\Other'))
        for pair in ((None, 'C:\\Games'), ('C:\\Games', None), ('', ''), (None, None)):
            self.assertIsNone(installs.same_folder(*pair))

    def test_a_broken_manifest_does_not_stop_discovery(self):
        (self.manifests / 'c.item').write_text('{not json', encoding='utf-8')
        self.assertEqual(list(installs.epic_entries()), [('Epic Games', str(self.epic))])


if __name__ == '__main__':
    unittest.main()
