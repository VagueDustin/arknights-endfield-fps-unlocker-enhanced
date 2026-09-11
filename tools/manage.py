"""Endfield Enhancer: inspect, install, configure, and restore an experimental build."""
import argparse
import configparser
import ctypes
import hashlib
import json
import os
from pathlib import Path
import tempfile
import uuid
from contextlib import contextmanager

from check_compatibility import inspect, pe_exports

STATE = '.endfield-enhancer'
COMPILER = 'd3dcompiler_47.dll'
ORIGINAL = 'endfield_original_compiler.dll'
PAYLOAD = 'endfield_fps.dll'
CONFIG = 'endfield-enhancer.ini'
OWNED = (COMPILER, ORIGINAL, PAYLOAD, CONFIG)
PRESETS = {'balanced': 120, 'high-refresh': 144, '240hz': 240, 'unlimited': -1}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def regular(path):
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f'Expected a regular file: {path.name}')


def atomic_write(path, data):
    regular(path)
    descriptor, temporary = tempfile.mkstemp(prefix='.enhancer-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def game_idle():
    if os.name != 'nt':
        raise ValueError('Installation is supported on Windows only')
    from ctypes import wintypes
    class Entry(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('usage', wintypes.DWORD),
                    ('pid', wintypes.DWORD), ('heap', ctypes.c_size_t),
                    ('module', wintypes.DWORD), ('threads', wintypes.DWORD),
                    ('parent', wintypes.DWORD), ('priority', wintypes.LONG),
                    ('flags', wintypes.DWORD), ('exe', wintypes.WCHAR * 260)]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        raise OSError('Cannot check running processes')
    try:
        entry = Entry()
        entry.size = ctypes.sizeof(entry)
        more = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        if not more:
            raise OSError('Cannot enumerate running processes')
        while more:
            if entry.exe.lower() in ('endfield.exe', 'arknights_endfield.exe'):
                raise ValueError('Close Endfield before installing or restoring files')
            more = kernel.Process32NextW(snapshot, ctypes.byref(entry))
        if ctypes.get_last_error() != 18:
            raise OSError('Process enumeration ended unexpectedly')
    finally:
        kernel.CloseHandle(snapshot)


@contextmanager
def locked(game):
    # A process-scoped OS lock cannot be left stale after a crash.
    if os.name != 'nt':
        yield
        return
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    name = hashlib.sha256(str(game).lower().encode()).hexdigest()
    handle = kernel.CreateMutexW(None, True, 'Local\\EndfieldEnhancer-' + name)
    if not handle:
        raise OSError('Cannot acquire installation lock')
    try:
        if ctypes.get_last_error() == 183:
            raise ValueError('Another manager is using this game folder')
        yield
    finally:
        kernel.CloseHandle(handle)


def settings(target=120, background=0, vsync=0):
    if target != -1 and not 30 <= target <= 1000:
        raise ValueError('FPS must be 30–1000, or -1 for unlimited')
    if background != 0 and not 30 <= background <= 1000:
        raise ValueError('Background FPS must be 0 (disabled) or 30–1000')
    if not -1 <= vsync <= 4:
        raise ValueError('VSync must be -1 (game setting) or 0–4')
    return (f'[FPS]\nTarget={target}\nBackground={background}\nVSync={vsync}\n'
            '\n[Graphics]\n; Overrides remain disabled until individually validated.\nEnabled=0\n').encode('ascii')


def state_path(game):
    state = game / STATE
    if state.is_symlink() or (state.exists() and not state.is_dir()):
        raise ValueError('Invalid installation state directory')
    # Also reject Windows directory junctions.
    if state.exists() and state.resolve().parent != game.resolve():
        raise ValueError('Installation state escapes the game directory')
    return state


def read_state(game):
    state = state_path(game)
    regular(state / 'manifest.json')
    manifest = json.loads((state / 'manifest.json').read_text())
    if manifest.get('schema') != 1 or set(manifest.get('installed', {})) != set(OWNED):
        raise ValueError('Invalid installation manifest; preserve backups for manual recovery')
    if manifest.get('phase') not in ('prepared', 'installed'):
        raise ValueError('Invalid installation phase')
    return state, manifest


def install(game, package, config):
    game_idle()
    report = inspect(game)
    if report['missing_required_exports']:
        raise ValueError('Required runtime APIs are unavailable')
    state = state_path(game)
    if state.exists():
        raise ValueError('Installation or recovery state exists; run restore before reinstalling')
    for name in OWNED:
        regular(game / name)
        if name != COMPILER and (game / name).exists():
            raise ValueError(f'File conflict: {name}; no files changed')
    if report['legacy_loader_files_present']:
        raise ValueError('Legacy mod files present; uninstall them before continuing')
    package_manifest = json.loads((package / 'package.json').read_text())
    if set(package_manifest['files']) != {COMPILER, PAYLOAD}:
        raise ValueError('Invalid build package manifest')
    for name, expected in package_manifest['files'].items():
        regular(package / name)
        if digest(package / name) != expected:
            raise ValueError(f'Package checksum mismatch: {name}')
    # Forward only to the compiler supplied by this game, preserving all named exports.
    if set(pe_exports(game / COMPILER)) != set(pe_exports(package / COMPILER)):
        raise ValueError('Compiler export mismatch; this loader does not match the installed compiler')
    original = (game / COMPILER).read_bytes()
    files = {COMPILER: (package / COMPILER).read_bytes(), ORIGINAL: original,
             PAYLOAD: (package / PAYLOAD).read_bytes(), CONFIG: config}
    manifest = {'schema': 1, 'phase': 'prepared',
                'original_sha256': hashlib.sha256(original).hexdigest(),
                'runtime_sha256': report['runtime_sha256'],
                'installed': {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}}
    state.mkdir()
    try:
        atomic_write(state / 'original.bin', original)
        atomic_write(state / 'manifest.json', json.dumps(manifest, indent=2).encode())
    except Exception:
        # No game file has changed yet. Preserve anything written for inspection.
        raise
    try:
        # Install the loader last, after all its dependencies exist.
        for name in (ORIGINAL, PAYLOAD, CONFIG, COMPILER):
            atomic_write(game / name, files[name])
        manifest['phase'] = 'installed'
        atomic_write(state / 'manifest.json', json.dumps(manifest, indent=2).encode())
    except Exception:
        restore(game)
        raise
    return {'status': 'installed_experimental', 'runtime_sha256': report['runtime_sha256']}


def restore(game):
    game_idle()
    state, manifest = read_state(game)
    backup = state / 'original.bin'
    regular(backup)
    if digest(backup) != manifest['original_sha256']:
        raise ValueError('Backup checksum mismatch; refusing to restore')
    # Preflight every file before touching any. Preserve game updates and other mods.
    for name in OWNED:
        path = game / name
        regular(path)
        if path.exists():
            allowed = {manifest['installed'][name]}
            if name == COMPILER:
                allowed.add(manifest['original_sha256'])
            if name == CONFIG:
                continue  # Configuration is user-editable and archived below.
            if digest(path) not in allowed:
                raise ValueError(f'{name} changed since installation; preserve it and the backup for manual recovery')
    if (game / CONFIG).exists():
        atomic_write(state / 'last-config.ini', (game / CONFIG).read_bytes())
    atomic_write(game / COMPILER, backup.read_bytes())
    for name in (ORIGINAL, PAYLOAD, CONFIG):
        (game / name).unlink(missing_ok=True)
    # Retain original bytes and last configuration outside the active state.
    destination = game / (STATE + '-restored')
    if destination.exists():
        destination = game / (STATE + '-restored-' + uuid.uuid4().hex)
    state.rename(destination)
    return {'status': 'restored', 'backup_directory': destination.name}


def configure(game, target=None, background=None, vsync=None):
    state, manifest = read_state(game)
    if manifest['phase'] != 'installed':
        raise ValueError('Incomplete installation; run restore first')
    regular(game / CONFIG)
    parser = configparser.ConfigParser()
    parser.read(game / CONFIG)
    old = parser['FPS']
    data = settings(old.getint('Target') if target is None else target,
                    old.getint('Background') if background is None else background,
                    old.getint('VSync') if vsync is None else vsync)
    atomic_write(game / CONFIG, data)
    return {'status': 'configured', 'note': 'Runtime reloads within one second. Graphics overrides remain disabled.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['inspect', 'install', 'restore', 'configure', 'profiles'])
    parser.add_argument('--game', type=Path)
    parser.add_argument('--package', type=Path, default=Path(__file__).resolve().parent)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--preset', choices=PRESETS)
    group.add_argument('--fps', type=int)
    parser.add_argument('--background', type=int)
    parser.add_argument('--vsync', type=int)
    args = parser.parse_args()
    if args.command == 'profiles':
        print(json.dumps({'fps_presets': PRESETS, 'graphics': {
            name: 'disabled: no validated implementation for this build'
            for name in ('anti_aliasing', 'shadows', 'ambient_occlusion', 'render_scale')}}, indent=2))
        return 0
    if not args.game:
        parser.error('--game is required')
    try:
        game = args.game.resolve(strict=True)
        fps = PRESETS[args.preset] if args.preset else args.fps
        with locked(game):
            if args.command == 'inspect':
                result = inspect(game)
                result['managed_installation'] = state_path(game).exists()
            elif args.command == 'install':
                result = install(game, args.package.resolve(), settings(
                    120 if fps is None else fps,
                    0 if args.background is None else args.background,
                    0 if args.vsync is None else args.vsync))
            elif args.command == 'configure':
                result = configure(game, fps, args.background, args.vsync)
            else:
                result = restore(game)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError, configparser.Error) as exc:
        parser.exit(2, f'{exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
