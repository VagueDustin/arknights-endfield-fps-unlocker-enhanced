"""Endfield Enhancer: inspect, install, configure, and restore an experimental build."""
import argparse
import configparser
import ctypes
import hashlib
import json
import os
import sys
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
GRAPHICS_DEFAULTS = dict.fromkeys(('Anisotropic', 'Sharpening', 'RenderScale',
                                  'ShadowResolution', 'AmbientOcclusion', 'TemporalAA'), -1)
GRAPHICS_PRESETS = {
    'game': dict(GRAPHICS_DEFAULTS),
    'crisp': dict(GRAPHICS_DEFAULTS, Anisotropic=2, Sharpening=20),
    'supersample': dict(GRAPHICS_DEFAULTS, Anisotropic=2, RenderScale=125),
}


def package_directory():
    return Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent


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


def settings(target=120, background=0, vsync=0, graphics=None):
    if target != -1 and not 30 <= target <= 1000:
        raise ValueError('FPS must be 30–1000, or -1 for unlimited')
    if background != 0 and not 30 <= background <= 1000:
        raise ValueError('Background FPS must be 0 (disabled) or 30–1000')
    if not -1 <= vsync <= 4:
        raise ValueError('VSync must be -1 (game setting) or 0–4')
    values = dict(GRAPHICS_DEFAULTS)
    if graphics:
        if set(graphics) - set(values):
            raise ValueError('Unknown graphics setting')
        values.update(graphics)
    if not all(isinstance(value, int) for value in values.values()):
        raise ValueError('Graphics settings must be integers')
    if values['Anisotropic'] not in (-1, 0, 1, 2):
        raise ValueError('Anisotropic filtering: -1 game, 0 off, 1 per-texture, 2 forced on')
    if not -1 <= values['Sharpening'] <= 100:
        raise ValueError('Sharpening must be -1 (game) or 0–100 percent')
    if values['RenderScale'] != -1 and not 50 <= values['RenderScale'] <= 200:
        raise ValueError('Render scale must be -1 (game) or 50–200 percent')
    if values['ShadowResolution'] not in (-1, 512, 1024, 2048, 4096):
        raise ValueError('Shadow resolution must be -1, 512, 1024, 2048, or 4096')
    if any(values[key] not in (-1, 0, 1) for key in ('AmbientOcclusion', 'TemporalAA')):
        raise ValueError('AO and TAAU must be -1 (game), 0 (off), or 1 (on)')
    return (f'[FPS]\nTarget={target}\nBackground={background}\nVSync={vsync}\n\n[Graphics]\n' +
            ''.join(f'{key}={value}\n' for key, value in values.items())).encode('ascii')


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
    if set(pe_exports(game / COMPILER, details=True)) != set(pe_exports(package / COMPILER, details=True)):
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
        # No game files changed; remove only files created in this new state directory.
        for name in ('manifest.json', 'original.bin'):
            (state / name).unlink(missing_ok=True)
        state.rmdir()
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


def configure(game, target=None, background=None, vsync=None, graphics=None):
    state, manifest = read_state(game)
    if manifest['phase'] != 'installed':
        raise ValueError('Incomplete installation; run restore first')
    regular(game / CONFIG)
    parser = configparser.ConfigParser()
    parser.read(game / CONFIG)
    old = parser['FPS']
    current_graphics = {key: parser.getint('Graphics', key, fallback=-1) for key in GRAPHICS_DEFAULTS}
    if graphics:
        current_graphics.update(graphics)
    data = settings(old.getint('Target') if target is None else target,
                    old.getint('Background') if background is None else background,
                    old.getint('VSync') if vsync is None else vsync, current_graphics)
    atomic_write(game / CONFIG, data)
    return {'status': 'configured', 'graphics': current_graphics,
            'note': 'FPS reloads within one second; graphics apply at a render callback after compatibility checks. See runtime log for readback.'}


def upgrade(game, package, config=None):
    game_idle()
    state, manifest = read_state(game)
    if manifest['phase'] != 'installed':
        raise ValueError('Incomplete installation; restore before upgrading')
    # Validate the new package before touching the current installation.
    incoming = json.loads((package / 'package.json').read_text())
    if set(incoming['files']) != {COMPILER, PAYLOAD}:
        raise ValueError('Invalid upgrade package')
    for name, expected in incoming['files'].items():
        if digest(package / name) != expected:
            raise ValueError('Upgrade package checksum mismatch')
    if set(pe_exports(state / 'original.bin', details=True)) != set(pe_exports(package / COMPILER, details=True)):
        raise ValueError('Compiler export mismatch in upgrade package')
    for name in OWNED:
        regular(game / name)
        if name != CONFIG and digest(game / name) != manifest['installed'][name]:
            raise ValueError(f'{name} changed; upgrade stopped')
    previous = state / 'previous-package'
    previous.mkdir(exist_ok=False)
    old_config = (game / CONFIG).read_bytes()
    for name in (COMPILER, PAYLOAD):
        atomic_write(previous / name, (game / name).read_bytes())
    atomic_write(previous / 'package.json', json.dumps({'version': 'previous-build', 'files': {
        name: manifest['installed'][name] for name in (COMPILER, PAYLOAD)}}).encode())
    restored = restore(game)
    archived = game / restored['backup_directory']
    try:
        result = install(game, package, old_config if config is None else config)
    except Exception as error:
        if not state_path(game).exists():
            install(game, archived / 'previous-package', old_config)
        raise RuntimeError(f'Upgrade failed; previous build restored when possible: {error}') from error
    new_state, new_manifest = read_state(game)
    new_manifest['previous_archive'] = archived.name
    atomic_write(new_state / 'manifest.json', json.dumps(new_manifest, indent=2).encode())
    result['previous_build_backup'] = archived.name
    return result


def rollback(game):
    _, manifest = read_state(game)
    archive = manifest.get('previous_archive', '')
    if not archive.startswith(STATE + '-restored') or Path(archive).name != archive:
        raise ValueError('No previous build is recorded')
    previous = game / archive
    if previous.resolve().parent != game.resolve():
        raise ValueError('Invalid previous-build path')
    return upgrade(game, previous / 'previous-package', (previous / 'last-config.ini').read_bytes())


def diagnostics(game):
    result = inspect(game)
    state = state_path(game)
    if state.exists():
        _, manifest = read_state(game)
        result['installation_phase'] = manifest['phase']
        result['runtime_changed_since_install'] = result['runtime_sha256'] != manifest['runtime_sha256']
        result['changed_or_missing_files'] = [name for name, expected in manifest['installed'].items()
            if name != CONFIG and (not (game / name).is_file() or digest(game / name) != expected)]
    else:
        result['installation_phase'] = 'not_installed'
    local = os.environ.get('LOCALAPPDATA')
    logs = sorted((Path(local) / 'EndfieldEnhancer').glob('runtime-*.log'),
                  key=lambda path: path.stat().st_mtime, reverse=True) if local else []
    result['latest_runtime_log'] = logs[0].name if logs else None
    result['latest_runtime_log_tail'] = logs[0].read_text(errors='replace').splitlines()[-30:] if logs else []
    result['log_note'] = 'Logs may belong to an earlier launch or the test harness; check timestamps.'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['inspect', 'install', 'restore', 'configure', 'profiles', 'diagnostics', 'upgrade', 'rollback'])
    parser.add_argument('--game', type=Path)
    parser.add_argument('--package', type=Path, default=package_directory())
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--preset', choices=PRESETS)
    group.add_argument('--fps', type=int)
    parser.add_argument('--background', type=int)
    parser.add_argument('--vsync', type=int)
    parser.add_argument('--graphics-preset', choices=GRAPHICS_PRESETS)
    for option in ('anisotropic', 'sharpening', 'render-scale', 'shadow-resolution', 'ambient-occlusion', 'temporal-aa'):
        parser.add_argument('--' + option, type=int)
    args = parser.parse_args()
    if args.command == 'profiles':
        print(json.dumps({'fps_presets': PRESETS, 'graphics_presets': GRAPHICS_PRESETS}, indent=2))
        return 0
    if not args.game:
        parser.error('--game is required')
    try:
        game = args.game.resolve(strict=True)
        fps = PRESETS[args.preset] if args.preset else args.fps
        graphics = dict(GRAPHICS_PRESETS[args.graphics_preset]) if args.graphics_preset else {}
        for field, key in (('anisotropic', 'Anisotropic'), ('sharpening', 'Sharpening'),
                           ('render_scale', 'RenderScale'), ('shadow_resolution', 'ShadowResolution'),
                           ('ambient_occlusion', 'AmbientOcclusion'), ('temporal_aa', 'TemporalAA')):
            if getattr(args, field) is not None:
                graphics[key] = getattr(args, field)
        with locked(game):
            if args.command == 'inspect':
                result = inspect(game)
                result['managed_installation'] = state_path(game).exists()
            elif args.command == 'install':
                result = install(game, args.package.resolve(), settings(
                    120 if fps is None else fps,
                    0 if args.background is None else args.background,
                    0 if args.vsync is None else args.vsync, graphics))
            elif args.command == 'configure':
                result = configure(game, fps, args.background, args.vsync, graphics)
            elif args.command == 'upgrade':
                result = upgrade(game, args.package.resolve())
            elif args.command == 'rollback':
                result = rollback(game)
            elif args.command == 'diagnostics':
                result = diagnostics(game)
            else:
                result = restore(game)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError, RuntimeError, configparser.Error) as exc:
        parser.exit(2, f'{exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
