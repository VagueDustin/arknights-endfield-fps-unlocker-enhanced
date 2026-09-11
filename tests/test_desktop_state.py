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
                locked.assert_called_once_with(game.resolve())

    def test_live_status_ignores_logs_from_another_process(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, LOCALAPPDATA=directory):
            folder=Path(directory)/'EndfieldEnhancer'; folder.mkdir()
            (folder/'runtime-123.log').write_text('Applied target=240')
            with patch('live_status.subprocess.run') as run:
                run.return_value.stdout='"Endfield.exe","456","Console","1","1 K"'
                result=live_status.snapshot(now=0)
                self.assertTrue(result['running']); self.assertIsNone(result['cap'])
                self.assertEqual(result['runtime'],'starting')
                (folder/'runtime-456.log').write_text('Applied target=144\nGraphics: render-loop callback active on thread 1')
                result=live_status.snapshot(now=1)
                self.assertEqual(result['cap'],144)
                self.assertEqual(result['graphics'],'Render loop connected')
                self.assertEqual(result['runtime'],'reporting')
                run.return_value.stdout='INFO: No tasks are running'
                self.assertFalse(live_status.snapshot(now=2)['running'])

    def test_live_status_flags_a_game_that_never_reports_a_runtime(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, LOCALAPPDATA=directory):
            (Path(directory)/'EndfieldEnhancer').mkdir()
            with patch('live_status.subprocess.run') as run:
                run.return_value.stdout='"Endfield.exe","789","Console","1","1 K"'
                early=live_status.snapshot(now=100)
                self.assertEqual(early['runtime'],'starting')
                late=live_status.snapshot(now=100+live_status.RUNTIME_GRACE_SECONDS+1)
                self.assertEqual(late['runtime'],'missing')
                self.assertEqual(late['graphics'],'Runtime not detected')
                self.assertGreaterEqual(late['runtime_seconds'],live_status.RUNTIME_GRACE_SECONDS)
                # A new game process starts the clock again.
                run.return_value.stdout='"Endfield.exe","790","Console","1","1 K"'
                self.assertEqual(live_status.snapshot(now=1000)['runtime'],'starting')

    def test_session_record_accumulates_states_per_game_process(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, LOCALAPPDATA=directory):
            self.assertIsNone(live_status.record_session({'running': False}))
            first = live_status.record_session({'running': True, 'pid': 7, 'runtime': 'starting', 'anticheat': 'running', 'runtime_seconds': 3, 'cap': None})
            second = live_status.record_session({'running': True, 'pid': 7, 'runtime': 'missing', 'anticheat': 'running', 'runtime_seconds': 50, 'cap': None})
            self.assertEqual(second['started'], first['started'])
            self.assertEqual(second['runtime_states'], ['starting', 'missing'])
            self.assertEqual(second['anticheat_states'], ['running'])
            self.assertEqual(second['seconds_observed'], 50)
            fresh = live_status.record_session({'running': True, 'pid': 8, 'runtime': 'reporting', 'anticheat': 'stopped', 'runtime_seconds': 1, 'cap': 144})
            self.assertEqual(fresh['runtime_states'], ['reporting'])
            self.assertEqual(json.loads(live_status.session_path().read_text())['pid'], 8)

    def test_anticheat_state_parses_service_control_manager_output(self):
        with patch('live_status._run') as run:
            run.return_value.returncode = 0
            run.return_value.stdout = 'SERVICE_NAME: AntiCheatExpert Protection\n        TYPE               : 110  WIN32_OWN_PROCESS  (interactive)\n        STATE              : 4  RUNNING\n'
            self.assertEqual(live_status.anticheat_state(), 'running')
            run.return_value.stdout = '        STATE              : 1  STOPPED \n'
            self.assertEqual(live_status.anticheat_state(), 'stopped')
            run.return_value.returncode = 1060
            run.return_value.stdout = '[SC] EnumQueryServicesStatus:OpenService FAILED 1060:\n\nThe specified service does not exist as an installed service.\n'
            self.assertEqual(live_status.anticheat_state(), 'absent')

    def test_live_status_reports_a_runtime_that_gave_up(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, LOCALAPPDATA=directory):
            folder=Path(directory)/'EndfieldEnhancer'; folder.mkdir()
            (folder/'runtime-42.log').write_text('Starting Fate Engine runtime 0.4.5.\nRequired Unity setters unavailable; no hooks installed.')
            with patch('live_status.subprocess.run') as run:
                run.return_value.stdout='"Endfield.exe","42","Console","1","1 K"'
                self.assertEqual(live_status.snapshot(now=0)['runtime'],'stopped')
