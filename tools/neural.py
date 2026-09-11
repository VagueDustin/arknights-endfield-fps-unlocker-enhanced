"""Conservative, game-local installation of the tested neural rendering components.

ReShade is a separately installed prerequisite. Never take ownership of existing
addons or overwrite the game's DLSS/Streamline libraries.
"""
import base64
import configparser
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import uuid

import manage

STATE = '.fate-engine-neural.json'
CONFIG = 'ReShade.ini'
SECTION = 'RenoDX.DLSS5'
BRIDGE = 'dlss5-bridge.cfg'
FILES = {
    'renodx-dlss5.addon64': '9150097cdee2953cdc9894d2e5606ea5100e6c8f95fc7bb1b407328b4391a07a',
    'dlss5-bridge.addon64': '11278e8afbcf81cd545e64d0fe8339ae830f5636d33fa998554076a96eef8a93',
    'nvngx_dlssnr.dll': 'e16bcf15e16e13f527491cdf7845b2fe6521a738d8f7c9c721866a8496e1fc8e',
}
OWNED = (*FILES, BRIDGE, CONFIG)
BRIDGE_DEFAULT = b'# dlss5-bridge keep\nvk_mirror=1\nstage=3\nmode=2\nunwrap=0\nsynth=0\n'


def safe_file(path):
    manage.regular(path)
    if path.exists() and getattr(path.stat(), 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
        raise ValueError(f'Reparse points are not supported: {path.name}')


def game_path(game):
    game = Path(game).resolve(strict=True)
    safe_file(game / 'Endfield.exe')
    if not (game / 'Endfield.exe').is_file():
        raise ValueError('Select the folder containing Endfield.exe')
    for name in (*OWNED, STATE, 'renodx-dlss.addon64'):
        safe_file(game / name)
    return game


def merge_settings(data, updates, missing_only=False):
    """Keep unrelated INI sections, comments, and user settings intact."""
    text = data.decode('utf-8-sig')
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    parser.optionxform = str
    parser.read_string(text)
    newline = '\r\n' if '\r\n' in text else '\n'
    lines = text.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines) if line.strip() == f'[{SECTION}]'), None)
    if start is None:
        if text and not text.endswith(('\n', '\r')):
            lines.append(newline)
        lines.extend([f'[{SECTION}]{newline}'])
        start = len(lines) - 1
    end = next((i for i in range(start + 1, len(lines)) if lines[i].lstrip().startswith('[')), len(lines))
    for key, value in updates.items():
        index = next((i for i in range(start + 1, end)
                      if re.match(r'^\s*' + re.escape(key) + r'\s*=', lines[i])), None)
        if index is not None:
            if not missing_only:
                lines[index] = f'{key}={value}{newline}'
        else:
            if end and not lines[end - 1].endswith(('\n', '\r')):
                lines[end - 1] += newline
            lines.insert(end, f'{key}={value}{newline}')
            end += 1
    result = ''.join(lines).encode('utf-8')
    return (b'\xef\xbb\xbf' if data.startswith(b'\xef\xbb\xbf') else b'') + result


def reshade_status(game):
    root = Path(os.environ.get('PROGRAMDATA', 'C:/ProgramData')) / 'ReShade'
    manifest = root / 'ReShade64.json'
    try:
        apps = (root / 'ReShadeApps.ini').read_text(encoding='utf-8-sig')
        entries = next((line[5:].split(',') for line in apps.splitlines() if line.startswith('Apps=')), [])
        enabled = str(game / 'Endfield.exe').casefold() in {p.strip().casefold() for p in entries}
        if not enabled or not manifest.is_file() or not (root / 'ReShade64.dll').is_file():
            return False
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Khronos\Vulkan\ImplicitLayers',
                            0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            value, kind = winreg.QueryValueEx(key, str(manifest))
        return value == 0 and kind == winreg.REG_DWORD
    except (OSError, ImportError):
        return False


def inspect(game):
    game = game_path(game)
    components = {name: ('Missing' if not (game / name).exists() else
                        'Tested version' if manage.digest(game / name) == expected else 'Unrecognized version')
                  for name, expected in FILES.items()}
    result = {'components': components, 'reshade_registered': reshade_status(game),
              'ownership': 'Fate Engine' if (game / STATE).exists() else 'External / unmanaged',
              'conflicting_addon': (game / 'renodx-dlss.addon64').exists(),
              'saved_enabled': None, 'toggle_key': None,
              'runtime': 'Not measured. Saved settings do not prove active neural rendering.'}
    if (game / CONFIG).exists():
        parser = configparser.ConfigParser(interpolation=None)
        parser.read_string((game / CONFIG).read_text(encoding='utf-8-sig'))
        if parser.has_section(SECTION):
            result['saved_enabled'] = parser.get(SECTION, 'NeuralUplift', fallback='Addon default')
            result['toggle_key'] = parser.get(SECTION, 'NRToggleKey', fallback='Addon default (F6)')
    if (game / STATE).exists():
        result['phase'] = read_state(game)['phase']
    return result


def read_state(game):
    safe_file(game / STATE)
    if not (game / STATE).exists():
        raise ValueError('No managed DLSS installation was found. This setup was installed outside Fate Engine; its files have been left unchanged.')
    state = json.loads((game / STATE).read_text(encoding='utf-8'))
    if state.get('schema') != 1 or state.get('game') != str(game):
        raise ValueError('Neural recovery record does not match this game')
    if set(state.get('files', {})) != set(OWNED):
        raise ValueError('Invalid neural recovery file list')
    for name, entry in state['files'].items():
        data = base64.b64decode(entry['before'], validate=True) if entry['before'] is not None else None
        if name != CONFIG and data is not None:
            raise ValueError('Only the pre-existing ReShade config may be restored')
        if entry['before_hash'] != (hashlib.sha256(data).hexdigest() if data is not None else None):
            raise ValueError('Neural backup checksum mismatch')
        if not re.fullmatch('[0-9a-f]{64}', entry['installed']):
            raise ValueError('Invalid installed checksum')
        if name in FILES and entry['installed'] != FILES[name]:
            raise ValueError('Unrecognized managed component')
    return state


def write_state(game, state):
    manage.atomic_write(game / STATE, json.dumps(state, indent=2).encode())


def install(game, source):
    game = game_path(game)
    with manage.locked(game):
        manage.game_idle()
        if (game / '.fate-engine-native-nr.json').exists() or (game / 'winmm.dll').exists():
            raise ValueError('Remove the native prototype or other winmm.dll setup before installing ReShade components. Existing files were left unchanged.')
        if (game / STATE).exists():
            raise ValueError('Neural installation is already managed. Remove it before reinstalling.')
        if not reshade_status(game):
            raise ValueError('Install ReShade with full addon support for Endfield Vulkan first. See DLSS setup instructions.')
        for name in (*FILES, BRIDGE, 'renodx-dlss.addon64'):
            if (game / name).exists():
                raise ValueError(f'Existing file preserved: {name}. This setup is not automatically adopted.')
        payloads = {}
        for name, expected in FILES.items():
            path = Path(source) / name
            safe_file(path)
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != expected:
                raise ValueError(f'Not the tested component: {name}')
            payloads[name] = data
        before_config = (game / CONFIG).read_bytes() if (game / CONFIG).exists() else None
        payloads[CONFIG] = merge_settings(before_config or b'', {'NRToggleKey': 45, 'NeuralUplift': 0}, missing_only=True)
        payloads[BRIDGE] = BRIDGE_DEFAULT
        state = {'schema': 1, 'game': str(game), 'phase': 'installing', 'files': {}}
        for name, data in payloads.items():
            before = before_config if name == CONFIG else None
            state['files'][name] = {'before': base64.b64encode(before).decode() if before is not None else None,
                                    'before_hash': hashlib.sha256(before).hexdigest() if before is not None else None,
                                    'installed': hashlib.sha256(data).hexdigest()}
        write_state(game, state)
        try:
            for name, data in payloads.items():
                manage.atomic_write(game / name, data)
            state['phase'] = 'installed'
            write_state(game, state)
        except Exception:
            # The journal permits recovery even if the process dies between writes.
            _restore(game)
            raise
    return {'message': 'Tested components installed. Existing settings preserved; new setups default to NR off and Insert.'}


def _restore(game):
    state = read_state(game)
    preserved = []
    for name, entry in state['files'].items():
        path = game / name
        safe_file(path)
        if not path.exists():
            continue
        current = manage.digest(path)
        if current not in (entry['installed'], entry['before_hash']):
            if name == CONFIG:
                preserved.append(name)
            else:
                raise ValueError(f'Changed file preserved; restoration stopped: {name}')
    for name, entry in state['files'].items():
        path = game / name
        if name in preserved:
            continue
        before = entry['before']
        if before is None:
            path.unlink(missing_ok=True)
        else:
            manage.atomic_write(path, base64.b64decode(before, validate=True))
    # Keep the journal as a permanent record of prior settings and file ownership.
    archive = game / ('.fate-engine-neural-restored-' + uuid.uuid4().hex + '.json')
    (game / STATE).rename(archive)
    return {'message': 'Managed neural files removed. ReShade and game libraries were left intact.',
            'preserved_user_settings': preserved, 'recovery_record': archive.name}


def restore(game):
    game = game_path(game)
    with manage.locked(game):
        if not (game / STATE).exists():
            return {'message': 'Nothing to remove: Fate Engine did not install these DLSS files. Your existing setup is unchanged. Use Inspect DLSS to view its status.'}
        manage.game_idle()
        return _restore(game)


def configure(game, enabled=None, insert=False):
    game = game_path(game)
    with manage.locked(game):
        manage.game_idle()
        status = inspect(game)
        if status.get('phase', 'installed') != 'installed':
            raise ValueError('An interrupted installation needs removal before changing settings')
        if status['conflicting_addon'] or any(v != 'Tested version' for v in status['components'].values()):
            raise ValueError('Settings require all three tested components and no conflicting addon')
        updates = {}
        if enabled is not None:
            updates['NeuralUplift'] = int(enabled)
        if insert:
            updates['NRToggleKey'] = 45
        original = (game / CONFIG).read_bytes() if (game / CONFIG).exists() else b''
        revised = merge_settings(original, updates)
        backup = game / ('.fate-engine-neural-settings-' + uuid.uuid4().hex + '.ini')
        manage.atomic_write(backup, original)
        manage.atomic_write(game / CONFIG, revised)
    return {'message': 'Saved for the next launch. Use the in-game hotkey for live toggling.', 'backup': backup.name}


def summary(result):
    """Human-readable panel status; detailed CLI output remains structured."""
    state = result.get('status', result)
    lines = [result['message'], ''] if 'message' in result else []
    if 'components' in state:
        labels = {'renodx-dlss5.addon64': 'Neural addon', 'dlss5-bridge.addon64': 'Vulkan bridge', 'nvngx_dlssnr.dll': 'NVIDIA NR runtime'}
        lines.extend(f'{labels[name]}: {value}' for name, value in state['components'].items())
        lines.append('ReShade: ' + ('Registered for this game' if state['reshade_registered'] else 'Setup needed'))
        lines.append('File management: ' + state['ownership'])
        if state['conflicting_addon']:
            lines.append('Conflict: newer neural addon is also present. Do not load both.')
        lines.append('Saved NR: ' + {'0': 'Off', '1': 'On'}.get(state['saved_enabled'], 'Addon default / unknown'))
        key = state['toggle_key']
        lines.append('Toggle: ' + ('Insert' if key == '45' else str(key or 'Addon default / unknown')))
        if state.get('phase', 'installed') != 'installed':
            lines.append('Recovery needed: interrupted installation.')
        lines.append('\nSaved settings only. Current neural execution is not measured.')
    if result.get('preserved_user_settings'):
        lines.append('Preserved modified ReShade settings.')
    return '\n'.join(lines)
