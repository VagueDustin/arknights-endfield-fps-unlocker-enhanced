"""Exercise the compiled native endpoint without loading anything into Endfield."""
import ctypes
from pathlib import Path
import subprocess
import time
import neural_live

def main():
    probe = Path(__file__).resolve().parents[1] / 'build/native-nr-audit/control_probe.exe'
    process = subprocess.Popen([str(probe)], stdout=subprocess.PIPE, text=True)
    try:
        pid = int(process.stdout.readline().strip())
        with neural_live.Connection(pid) as connection:
            values = dict(enabled=1,style=2,preset=3,intensity=.75,structure=.5,tone=1.25,skin=-1,auto_mask=1)
            state = connection.apply(values)
            assert state['settings'] == values, state
            assert state['frames'] == 0 and state['evaluated'] == 0, state
            values['enabled'] = 0
            state = connection.apply(values)
            assert state['settings']['enabled'] == 0, state
            # Inject a malformed packet to verify validation in C++, not only Python.
            revision = state['accepted'] + 2
            connection.publish_revision(revision - 1)
            ctypes.c_uint32.from_address(connection.address + 32).value = 99
            connection.publish_revision(revision)
            time.sleep(.15)
            rejected = connection.snapshot()
            assert rejected['rejected'] == revision, rejected
            assert rejected['settings'] == state['settings'], rejected
        print('PASS: native acknowledgement, exact settings readback, disable, malformed request rejection, no false rendered status')
    finally:
        process.terminate()
        process.wait(timeout=5)

if __name__ == '__main__':main()
