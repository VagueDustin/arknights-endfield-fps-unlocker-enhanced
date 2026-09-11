"""Inspect PE exports and config-name evidence without loading third-party code."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from check_compatibility import pe_exports


def audit(path):
    data = path.read_bytes()
    exports = pe_exports(path)
    strings = {value.decode('ascii') for value in re.findall(rb'[\x20-\x7e]{5,}', data)}
    return {
        'file': path.name,
        'sha256': hashlib.sha256(data).hexdigest(),
        'exports': exports,
        'reshade_symbols': sorted(value for value in strings if re.fullmatch(r'ReShade[A-Za-z0-9_]+', value)),
        'setting_names_present': sorted(strings & {'NRPreset', 'NRStyle', 'NRIntensity', 'NRLocalTone',
                                                   'NRLocalStructure', 'NRToggleKey', 'NeuralUplift'}),
        'note': 'Exports and strings establish interface evidence only, not ABI validity, live control, or rendering compatibility.',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', type=Path, nargs='+')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = json.dumps({'schema': 1, 'binaries': [audit(path) for path in args.files]}, indent=2)
    if args.output:
        args.output.write_text(report + '\n', encoding='utf-8')
    else:
        print(report)
