"""Read live runtime evidence without touching game memory."""
import csv
import os
from pathlib import Path
import re
import subprocess


def snapshot():
    result = {'running': False, 'pid': None, 'cap': None, 'graphics': 'Waiting for game', 'lines': []}
    process = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Endfield.exe', '/FO', 'CSV', '/NH'],
                             capture_output=True, text=True, timeout=8, creationflags=subprocess.CREATE_NO_WINDOW)
    for row in csv.reader(process.stdout.splitlines()):
        if len(row) > 1 and row[0].lower() == 'endfield.exe':
            result.update(running=True, pid=int(row[1]))
            break
    if not result['running']:
        return result
    path = Path(os.environ['LOCALAPPDATA']) / 'EndfieldEnhancer' / f"runtime-{result['pid']}.log"
    result['graphics'] = 'Waiting for runtime'
    if path.is_file():
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
    return result
