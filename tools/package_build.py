"""Write integrity metadata for DLLs just compiled by this source tree."""
import hashlib
import json
from pathlib import Path
import sys

package = Path(sys.argv[1])
files = {}
for name in ('d3dcompiler_47.dll', 'endfield_fps.dll'):
    with (package / name).open('rb') as stream:
        files[name] = hashlib.file_digest(stream, 'sha256').hexdigest()
(package / 'package.json').write_text(json.dumps({'version': '0.3.2', 'files': files}, indent=2))
