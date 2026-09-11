"""Versioned native NR control transport, independent of the renderer implementation."""
import ctypes
import math
import os
import struct
import time

SETTINGS = struct.Struct('<IIIffffI')
MAGIC = 0x524E4546
SIZE = 128
KEYS = ('enabled', 'style', 'preset', 'intensity', 'structure', 'tone', 'skin', 'auto_mask')

def encode(values):
    values = dict(values)
    for key, maximum in [('enabled', 1), ('style', 2), ('preset', 3), ('auto_mask', 1)]:
        value = values[key]
        if isinstance(value, float) and not value.is_integer():
            raise ValueError(key + ' must be an integer')
        values[key] = int(value)
        if not 0 <= values[key] <= maximum:
            raise ValueError(key + ' is outside the supported range')
    for key in ('intensity', 'structure', 'tone', 'skin'):
        values[key] = float(values[key])
        if not math.isfinite(values[key]) or not (-1 if key == 'skin' else 0) <= values[key] <= 2:
            raise ValueError(key + ' is outside the supported range')
    return SETTINGS.pack(*(values[key] for key in KEYS))

def decode(data):
    return dict(zip(KEYS, SETTINGS.unpack(data)))

class Connection:
    def __init__(self, pid):
        if os.name != 'nt':
            raise OSError('Native NR control requires Windows')
        self.api = ctypes.WinDLL('kernel32', use_last_error=True)
        self.api.OpenFileMappingW.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_wchar_p]
        self.api.OpenFileMappingW.restype = ctypes.c_void_p
        self.api.MapViewOfFile.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_size_t]
        self.api.MapViewOfFile.restype = ctypes.c_void_p
        self.api.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
        self.api.CloseHandle.argtypes = [ctypes.c_void_p]
        self.api.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
        self.api.CreateMutexW.restype = ctypes.c_void_p
        self.api.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        self.api.ReleaseMutex.argtypes = [ctypes.c_void_p]
        self.api.GetTickCount64.restype = ctypes.c_uint64
        self.handle = self.api.OpenFileMappingW(6, False, 'Local\\FateEngine.NR.' + str(int(pid)))
        self.address = None
        self.mutex = None
        if not self.handle:
            raise RuntimeError('Native NR backend is not connected. Launch with the native prototype installed.')
        self.address = self.api.MapViewOfFile(self.handle, 6, 0, 0, SIZE)
        if not self.address:
            self.close()
            raise ctypes.WinError(ctypes.get_last_error())
        header = ctypes.string_at(self.address, 24)
        magic, version, actual_pid, size, self.session = struct.unpack('<IIIIQ', header)
        if (magic, version, actual_pid, size) != (MAGIC, 1, int(pid), SIZE):
            self.close()
            raise RuntimeError('Incompatible native NR backend')
        self.mutex = self.api.CreateMutexW(None, False, 'Local\\FateEngine.NR.Writer.' + str(int(pid)))
        if not self.mutex:
            self.close()
            raise RuntimeError('Could not create NR writer lock')

    def close(self):
        if self.mutex:
            self.api.CloseHandle(self.mutex)
            self.mutex = None
        if self.address:
            self.api.UnmapViewOfFile(self.address)
            self.address = None
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None

    def __enter__(self): return self
    def __exit__(self, *args): self.close()

    def snapshot(self):
        for _ in range(20):
            raw = ctypes.string_at(self.address, SIZE)
            sequence = struct.unpack_from('<I', raw, 60)[0]
            after = ctypes.c_uint32.from_address(self.address + 60).value
            if sequence & 1 or sequence != after:
                continue
            accepted, evaluated, rejected = struct.unpack_from('<III', raw, 64)
            heartbeat, frames = struct.unpack_from('<QQ', raw, 112)
            if not heartbeat or self.api.GetTickCount64() - heartbeat > 5000:
                raise RuntimeError('Native NR renderer is not responding')
            return dict(accepted=accepted, evaluated=evaluated, rejected=rejected,
                        settings=decode(raw[76:108]), frames=frames, session=self.session,
                        failed=bool(struct.unpack_from('<I',raw,108)[0]))
        raise RuntimeError('Native NR status is busy; try again')

    def apply(self, values, timeout=3):
        packet = encode(values)
        if self.api.WaitForSingleObject(self.mutex, 1000) not in (0, 0x80):
            raise RuntimeError('Another Fate Engine window is updating NR settings')
        try:
            return self._apply(packet, timeout)
        finally:
            self.api.ReleaseMutex(self.mutex)

    def publish_revision(self, revision):
        # Windows x64 guarantees aligned 32-bit stores are atomic. x64 stores
        # preserve order; each ctypes call completes before the next starts.
        ctypes.c_uint32.from_address(self.address + 24).value = revision

    def _apply(self, packet, timeout):
        self.snapshot()
        # A single UI writer publishes odd while editing and even when complete.
        old = ctypes.c_uint32.from_address(self.address + 24).value
        revision = (old + 2) & 0x7ffffffe or 2
        self.publish_revision(revision - 1)
        ctypes.memmove(self.address + 28, packet, len(packet))
        self.publish_revision(revision)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            state = self.snapshot()
            if state['rejected'] == revision:
                raise RuntimeError('Native renderer rejected these settings')
            if state['accepted'] == revision:
                state['requested_revision'] = revision
                return state
            time.sleep(.05)
        raise RuntimeError('Settings were sent but the renderer has not acknowledged them')

def describe(state):
    rendered = state['accepted'] != 0 and state['evaluated'] == state['accepted']
    status = 'Last successful NR evaluation used this request' if rendered else 'Settings accepted; rendering not yet confirmed'
    if not state['settings']['enabled']:status = 'Neural rendering is disabled'
    if state.get('failed'):status = 'Native NR failed. Check OptiScaler.log; restart the game before retrying.'
    settings=state['settings']
    style=('Standard','Natural','Cinematic')[settings['style']]
    return status + '\nStyle: ' + style + '   |   Strength: ' + format(settings['intensity'],'.2f') + '\nSuccessful NR evaluations: ' + str(state['frames'])
