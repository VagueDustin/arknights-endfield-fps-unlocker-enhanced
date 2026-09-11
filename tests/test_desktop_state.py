import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import desktop_state
import live_status

class DesktopStateTests(unittest.TestCase):
    def test_remember_deduplicates_and_restores_only_managed_games(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, LOCALAPPDATA=directory):
            game = Path(directory) / 'game'; game.mkdir()
            desktop_state.remember(game); desktop_state.remember(game)
            self.assertEqual(json.loads(desktop_state.location().read_text())['games'], [str(game.resolve())])
            self.assertEqual(desktop_state.selected(), str(game.resolve()))
            self.assertEqual(desktop_state.restore_recorded(), {'restored': []})
            (game / '.endfield-enhancer').mkdir()
            with patch('manage.locked') as locked, patch('manage.restore', side_effect=ValueError('changed file')):
                with self.assertRaisesRegex(ValueError, 'changed file'):
                    desktop_state.restore_recorded()
                locked.assert_called_once_with(game)

    def test_live_status_ignores_logs_from_another_process(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, LOCALAPPDATA=directory):
            folder=Path(directory)/'EndfieldEnhancer'; folder.mkdir()
            (folder/'runtime-123.log').write_text('Applied target=240')
            with patch('live_status.subprocess.run') as run:
                run.return_value.stdout='"Endfield.exe","456","Console","1","1 K"'
                result=live_status.snapshot()
                self.assertTrue(result['running']); self.assertIsNone(result['cap'])
                (folder/'runtime-456.log').write_text('Applied target=144\nGraphics: render-loop callback active on thread 1')
                result=live_status.snapshot()
                self.assertEqual(result['cap'],144)
                self.assertEqual(result['graphics'],'Render loop connected')
                run.return_value.stdout='INFO: No tasks are running'
                self.assertFalse(live_status.snapshot()['running'])
