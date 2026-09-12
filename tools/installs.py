"""Find every Arknights: Endfield installation on this PC.

A player can have the Epic build and the official Gryphline launcher build side by
side. Managing the wrong one is indistinguishable from a broken installation: the
files are patched correctly, the game launches, and nothing ever loads them. So the
app discovers every install, prefers the one the game actually last ran from, and
says so when the choice is ambiguous.
"""
import json
import os
from pathlib import Path

EXE = 'Endfield.exe'
# Display names used by the official launcher and its game entry in the uninstall list.
LAUNCHER_NAMES = ('gryphlink', 'gryphline', 'endfield', 'arknights')
UNINSTALL_KEY = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'


def same_folder(left, right):
    """True, False, or None when either side is unknown. Case-insensitive on Windows."""
    if not left or not right:
        return None
    try:
        return os.path.normcase(os.path.abspath(str(left))) == os.path.normcase(os.path.abspath(str(right)))
    except (OSError, ValueError):
        return None


def game_folders(location):
    """Endfield.exe sits in the install root or under a launcher's games folder."""
    root = Path(str(location))
    candidates = [root, root / 'games' / 'EndField Game']
    try:
        candidates.extend(sorted((root / 'games').iterdir()))
    except OSError:
        pass
    seen = set()
    for candidate in candidates:
        key = os.path.normcase(str(candidate))
        if key in seen:
            continue
        seen.add(key)
        try:
            if (candidate / EXE).is_file():
                yield candidate
        except OSError:
            continue


def epic_entries():
    """(source, install location) from the Epic Games launcher manifests."""
    manifests = Path(os.environ.get('PROGRAMDATA', 'C:/ProgramData')) / 'Epic/EpicGamesLauncher/Data/Manifests'
    try:
        files = sorted(manifests.glob('*.item'))
    except OSError:
        return
    for path in files:
        try:
            data = json.loads(path.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError):
            continue
        location = str(data.get('InstallLocation', ''))
        if location and 'endfield' in str(data.get('DisplayName', '')).lower():
            yield 'Epic Games', location


def uninstall_entries():
    """(display name, install location) pairs from the Windows uninstall list."""
    if os.name != 'nt':
        return
    import winreg
    views = [(winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_32KEY),
             (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_64KEY),
             (winreg.HKEY_CURRENT_USER, 0)]
    for hive, view in views:
        try:
            with winreg.OpenKey(hive, UNINSTALL_KEY, 0, winreg.KEY_READ | view) as key:
                count = winreg.QueryInfoKey(key)[0]
                for index in range(count):
                    try:
                        name = winreg.EnumKey(key, index)
                        with winreg.OpenKey(key, name) as entry:
                            yield (str(winreg.QueryValueEx(entry, 'DisplayName')[0]),
                                   str(winreg.QueryValueEx(entry, 'InstallLocation')[0]))
                    except OSError:
                        continue
        except OSError:
            continue


def launcher_entries():
    """(source, install location) for the official launcher and its game entries."""
    for name, location in uninstall_entries():
        if location and any(word in name.lower() for word in LAUNCHER_NAMES):
            yield name.strip() or 'Official launcher', location


def find_games():
    """[(source, folder)] for every distinct installation found on this PC."""
    found = {}
    for source, location in (*epic_entries(), *launcher_entries()):
        for folder in game_folders(location):
            found.setdefault(os.path.normcase(str(folder)), (source, str(folder)))
    return list(found.values())


def last_launched():
    """The folder Endfield actually started from most recently, or None."""
    try:
        import neural
        return neural.last_launch_folder()
    except Exception:
        return None


def find_game():
    """The installation to preselect: whichever one the game last actually ran from."""
    games = find_games()
    if not games:
        return ''
    last = last_launched()
    for _, folder in games:
        if same_folder(folder, last):
            return folder
    return games[0][1]
