"""Read live runtime evidence without touching game memory."""
import csv
import ctypes
import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import time

import installs

# A running game that has produced no runtime log after this long is reported as
# "runtime not detected" so users learn about a blocked or missing loader early.
RUNTIME_GRACE_SECONDS = 45
# Log lines written by the runtime when it gives up. See src/modern/runtime.cpp.
RUNTIME_STOP_MARKERS = ('no hooks installed', 'Timed out', 'Configuration missing',
                        'Hook setup failed', 'MinHook initialization failed',
                        'stopping overrides', 'Invalid setter addresses')
# Endfield ships Tencent's Anti-Cheat Expert. Its service state during a session is
# support evidence when the runtime or ReShade never loads; nothing here changes it.
ANTICHEAT_SERVICE = 'AntiCheatExpert Protection'
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_first_seen = {}


def log_directory():
    return Path(os.environ['LOCALAPPDATA']) / 'EndfieldEnhancer'


def _run(arguments):
    return subprocess.run(arguments, capture_output=True, text=True, timeout=8,
                          creationflags=subprocess.CREATE_NO_WINDOW)


def anticheat_state():
    """running, stopped, absent, or unknown; a read-only Service Control Manager query."""
    try:
        process = _run(['sc', 'query', ANTICHEAT_SERVICE])
    except (OSError, subprocess.SubprocessError):
        return 'unknown'
    if process.returncode == 1060 or 'does not exist' in process.stdout:
        return 'absent'
    match = re.search(r'STATE\s*:\s*\d+\s+(\w+)', process.stdout)
    return match[1].lower() if match else 'unknown'


def process_path(pid):
    """Full image path of a running process, or None.

    A read-only query that needs no elevation for the user's own processes. This is
    how the app tells which Endfield installation is actually running when a PC has
    more than one.
    """
    if os.name != 'nt':
        return None
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                                  wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
    if not handle:
        return None
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return None
        return buffer.value or None
    finally:
        kernel.CloseHandle(handle)


def snapshot(now=None, game=None):
    """Describe the running game and what its runtime log reports.

    ``runtime`` is one of: idle (game closed), starting (game up, no log yet),
    reporting (log present), stopped (log shows the runtime gave up), or
    missing (game up longer than the grace period without any log).
    ``install_match`` is False when the running game is a different installation
    than the managed ``game`` folder, which no runtime could ever attach to.
    """
    now = time.monotonic() if now is None else now
    result = {'running': False, 'pid': None, 'cap': None, 'graphics': 'Waiting for game',
              'lines': [], 'runtime': 'idle', 'runtime_seconds': 0,
              'image_path': None, 'install_match': None}
    process = _run(['tasklist', '/FI', 'IMAGENAME eq Endfield.exe', '/FO', 'CSV', '/NH'])
    for row in csv.reader(process.stdout.splitlines()):
        if len(row) > 1 and row[0].lower() == 'endfield.exe':
            result.update(running=True, pid=int(row[1]))
            break
    if not result['running']:
        _first_seen.clear()
        return result
    pid = result['pid']
    first = _first_seen.setdefault(pid, now)
    for stale in [key for key in _first_seen if key != pid]:
        del _first_seen[stale]
    result['runtime_seconds'] = int(now - first)
    result['anticheat'] = anticheat_state()
    result['image_path'] = process_path(pid)
    if result['image_path']:
        result['install_match'] = installs.same_folder(os.path.dirname(result['image_path']), game)
    path = log_directory() / f'runtime-{pid}.log'
    result['graphics'] = 'Waiting for runtime'
    if path.is_file():
        result['runtime'] = 'reporting'
        with path.open('rb') as stream:
            stream.seek(max(0, path.stat().st_size - 32768))
            lines = stream.read().decode('utf-8', errors='replace').splitlines()
        result['lines'] = lines[-60:]
        for line in lines:
            match = re.search(r'Applied target=(-?\d+)', line)
            if match:
                result['cap'] = int(match[1])
            if 'callback active' in line:
                result['graphics'] = 'Render loop connected'
            elif 'waiting for' in line and 'callback' in line:
                result['graphics'] = 'Graphics callback pending'
            elif 'graphics disabled' in line:
                result['graphics'] = 'Graphics unavailable on this build'
            if any(marker in line for marker in RUNTIME_STOP_MARKERS):
                result['runtime'] = 'stopped'
    elif now - first > RUNTIME_GRACE_SECONDS:
        result['runtime'] = 'missing'
        result['graphics'] = 'Runtime not detected'
    else:
        result['runtime'] = 'starting'
    return result


def session_path():
    return log_directory() / 'last-session.json'


def record_session(data):
    """Keep a small record of the most recent game session for the diagnostics report.

    Called by the desktop watcher while the game runs. It answers the support questions
    the runtime log cannot: which installation ran, how long, whether the runtime ever
    reported, and whether the anti-cheat service was running at the time.
    """
    if not data.get('running'):
        return None
    path = session_path()
    record = {}
    try:
        record = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        pass
    now = datetime.datetime.now().isoformat(timespec='seconds')
    if record.get('pid') != data['pid']:
        record = {'pid': data['pid'], 'started': now, 'runtime_states': [], 'anticheat_states': []}
    record['last_seen'] = now
    record['seconds_observed'] = data.get('runtime_seconds', 0)
    record['cap'] = data.get('cap')
    record['image_path'] = data.get('image_path')
    record['install_match'] = data.get('install_match')
    for key, value in (('runtime_states', data.get('runtime')), ('anticheat_states', data.get('anticheat'))):
        if value and value not in record[key]:
            record[key].append(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(record, indent=2), encoding='utf-8')
    os.replace(temporary, path)
    return record
