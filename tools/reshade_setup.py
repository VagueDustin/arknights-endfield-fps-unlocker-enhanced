"""Launch the official ReShade wizard; never edit its shared Vulkan registration."""
from pathlib import Path
import subprocess
import sys
import webbrowser
import manage
import neural

SETUP_NAME = 'ReShade_Setup_6.8.0_Addon.exe'
SETUP_HASH = 'afe4c8f13048306307983b8b3d41d5bf00a86820440b0e57dea10950e1176445'

def package_root():
    return Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1] / 'build/reshade-preview/package'

def component_folder():
    folder = package_root() / 'neural-components'
    return folder if all((folder / name).is_file() for name in neural.FILES) else None

def launch(game):
    game = neural.game_path(game)
    manage.game_idle()
    setup = package_root() / 'prerequisites' / SETUP_NAME
    if not setup.exists():
        webbrowser.open('https://reshade.me/#download')
        return 'Download ReShade with full addon support, then install for Endfield.exe using Vulkan.'
    neural.safe_file(setup)
    if manage.digest(setup) != SETUP_HASH:
        raise ValueError('Bundled ReShade setup failed verification. Reinstall Fate Engine before opening it.')
    subprocess.Popen([str(setup), str(game / 'Endfield.exe'), '--api', 'vulkan'], cwd=setup.parent)
    return 'Complete the ReShade wizard, then return here and install DLSS components.'
