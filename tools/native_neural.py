"""Reversible installation of the private, bundled native Vulkan NR prototype."""
import json
import base64
import ctypes
import hashlib
from pathlib import Path
import sys
import manage
import neural

STATE = '.fate-engine-native-nr.json'
FILES = ('winmm.dll', 'nvngx.dll_dlssnr.dll', 'nvngx_dlssnr.dll', 'OptiScaler.ini',
         'msvcp140.dll', 'msvcp140_atomic_wait.dll', 'vcruntime140.dll', 'vcruntime140_1.dll')
CONFLICTS = ('OptiScaler.dll', 'renodx-dlss5.addon64', 'renodx-dlss.addon64', 'dlss5-bridge.addon64')

def file_version(path):
    api=ctypes.WinDLL('version',use_last_error=True)
    api.GetFileVersionInfoSizeW.argtypes=[ctypes.c_wchar_p,ctypes.c_void_p]
    api.GetFileVersionInfoW.argtypes=[ctypes.c_wchar_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p]
    api.VerQueryValueW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(ctypes.c_uint)]
    size=api.GetFileVersionInfoSizeW(str(path),None)
    if not size:raise ValueError('Cannot verify Microsoft runtime version: '+path.name)
    data=ctypes.create_string_buffer(size)
    pointer=ctypes.c_void_p();length=ctypes.c_uint()
    if not api.GetFileVersionInfoW(str(path),0,size,data) or not api.VerQueryValueW(data,'\\',ctypes.byref(pointer),ctypes.byref(length)) or length.value<52:
        raise ValueError('Cannot read Microsoft runtime version: '+path.name)
    info=ctypes.cast(pointer,ctypes.POINTER(ctypes.c_uint32))
    if info[0]!=0xFEEF04BD:raise ValueError('Invalid runtime version data')
    return (info[2]>>16,info[2]&65535,info[3]>>16,info[3]&65535)

def payload():
    root = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1] / 'build/native-preview/package'
    return root / 'native-nr'

def game_path(game):
    game = neural.game_path(game)
    for name in (*FILES, *CONFLICTS, STATE):neural.safe_file(game / name)
    return game

def install(game, source=None):
    game = game_path(game)
    source = Path(source) if source else payload()
    manifest = json.loads((source / 'manifest.json').read_text())
    hashes = manifest['files']
    if set(hashes) != set(FILES):raise ValueError('Invalid native package file list')
    for name in FILES:
        neural.safe_file(source / name)
        if manage.digest(source / name) != hashes[name]:raise ValueError('Native package checksum mismatch: ' + name)
    with manage.locked(game):
        manage.game_idle()
        if (game / STATE).exists():raise ValueError('Remove the managed native prototype before upgrading.')
        for name in (*FILES[:4], *CONFLICTS):
            if (game / name).exists():raise ValueError('Existing file left unchanged: ' + name)
        if neural.reshade_status(game):raise ValueError('Remove the registered ReShade installation before testing the native backend.')
        owned=dict(hashes);before={};reused=[]
        for name in FILES[4:]:
            existing=game/name
            if not existing.exists():continue
            if manage.digest(existing)==hashes[name] or file_version(existing)>=file_version(source/name):
                owned.pop(name);reused.append(name)
            else:
                original=existing.read_bytes()
                before[name]={'data':base64.b64encode(original).decode(),'sha256':hashlib.sha256(original).hexdigest()}
        record = dict(schema=2, game=str(game), files=owned, before=before, reused=reused, phase='installing')
        manage.atomic_write(game / STATE, json.dumps(record, indent=2).encode())
        try:
            # Load the backend only after all dependencies and configuration exist.
            for name in (*FILES[1:], FILES[0]):
                if name in owned:manage.atomic_write(game / name, (source / name).read_bytes())
            record['phase'] = 'installed'
            manage.atomic_write(game / STATE, json.dumps(record, indent=2).encode())
        except Exception:
            restore_files(game, record)
            raise
    return 'Setup complete\nLaunch Endfield with DLSS enabled. Use the picture controls here, or press Insert in game to toggle the effect.\nNeural rendering starts off.'

def restore_files(game, record):
    names=set(record.get('files',{}));schema=record.get('schema')
    if schema not in (1,2) or record.get('game') != str(game) or not set(FILES[:4])<=names<=set(FILES) or (schema==1 and names!=set(FILES)):
        raise ValueError('Invalid native recovery record')
    backups={}
    for name,entry in record.get('before',{}).items():
        if name not in FILES[4:] or name not in names:raise ValueError('Invalid native backup file')
        data=base64.b64decode(entry['data'],validate=True)
        if hashlib.sha256(data).hexdigest()!=entry['sha256']:raise ValueError('Native backup checksum mismatch')
        backups[name]=data
    for name, checksum in record['files'].items():
        neural.safe_file(game / name)
        allowed={checksum}
        if name in backups:allowed.add(hashlib.sha256(backups[name]).hexdigest())
        if (game / name).exists() and manage.digest(game / name) not in allowed:
            raise ValueError('Native file changed after installation; left unchanged: ' + name)
    for name in FILES:
        if name not in names:continue
        if name in backups:manage.atomic_write(game/name,backups[name])
        else:(game / name).unlink(missing_ok=True)
    (game / STATE).unlink()

def restore(game):
    game = game_path(game)
    with manage.locked(game):
        manage.game_idle()
        if not (game / STATE).exists():return 'No managed native installation found.'
        restore_files(game, json.loads((game / STATE).read_text()))
    return 'Neural rendering removed. Any upgraded Microsoft runtime files were restored from backup.'

def inspect(game):
    game=game_path(game)
    if not (game/STATE).exists():
        return 'Not installed\nClose Endfield, then choose Set up neural rendering.\nReShade is not needed for this setup.'
    record=json.loads((game/STATE).read_text())
    if not set(FILES[:4])<=set(record.get('files',{}))<=set(FILES):raise ValueError('Invalid native recovery file list')
    changed=[name for name,digest in record['files'].items() if not (game/name).exists() or manage.digest(game/name)!=digest]
    if changed:return 'Installation needs attention\nMissing or changed: '+', '.join(changed)
    return 'Installed - ready to launch\nLaunch Endfield with DLSS enabled, then choose Check status.\nInsert toggles neural rendering. Live rendering has not been checked.'
