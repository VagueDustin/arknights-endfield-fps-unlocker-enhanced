"""Collect bundled Python distribution license files for the binary package."""
from importlib.metadata import distribution
from pathlib import Path
import shutil
import sys
out=Path(sys.argv[1])/'licenses'
for name in ('customtkinter','darkdetect','Pillow','pyinstaller'):
    dist=distribution(name)
    for entry in dist.files or []:
        if any(word in str(entry).lower() for word in ('license','copying','copyright')) and dist.locate_file(entry).is_file():
            target=out/name/Path(str(entry)).name
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(dist.locate_file(entry),target)
