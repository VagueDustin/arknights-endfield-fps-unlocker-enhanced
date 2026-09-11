from pathlib import Path
import sys, shutil, json, urllib.request
sys.path.insert(0,'tools')
import neural, manage, reshade_setup
root=Path.cwd();dest=root/'build/reshade-preview/package'
components=dest/'neural-components';components.mkdir(parents=True,exist_ok=True)
for name,expected in neural.FILES.items():
    src=root/'build/dlss5-lab-455'/name
    if name=='nvngx_dlssnr.dll':src=root/'build/dlss5-lab/nvidia-runtime-inspection'/name
    assert manage.digest(src)==expected, name
    shutil.copy2(src,components/name)
prereq=dest/'prerequisites';prereq.mkdir(exist_ok=True)
setup=root/'build/dlss5-lab'/reshade_setup.SETUP_NAME
assert manage.digest(setup)==reshade_setup.SETUP_HASH
shutil.copy2(setup,prereq/setup.name)
licenses=dest/'licenses';licenses.mkdir(exist_ok=True)
license_data=urllib.request.urlopen('https://raw.githubusercontent.com/crosire/reshade/main/LICENSE.md',timeout=30).read()
(licenses/'ReShade-BSD-3-Clause.txt').write_bytes(license_data)
shutil.copy2(root/'build/native-nr-audit/bridge/LICENSE',licenses/'DLSS5-Bridge-LICENSE.txt')
(components/'THIRD-PARTY-COMPONENTS.txt').write_text('Bundled with permission confirmed by the project maintainer. Krish/RenoDX addon, NIGos bridge, and NVIDIA runtime retain their authors rights and licenses. See THIRD_PARTY_NOTICES.md and licenses.\n')
manifest={'files':{str(p.relative_to(dest)):manage.digest(p) for p in [*(components/name for name in neural.FILES),prereq/setup.name]}}
(dest/'reshade-payload.json').write_text(json.dumps(manifest,indent=2))
print('Bundled ReShade payload staged and all four binary hashes verified.')
