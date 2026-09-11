"""Stage a PRIVATE local native NR bundle from the audited source and user runtime."""
import configparser
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
import native_neural

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'build/native-nr-audit/optiscaler'
DEST = ROOT / 'build/native-preview/package/native-nr'

def main():
    DEST.mkdir(parents=True, exist_ok=True)
    runtime = ROOT / 'build/dlss5-lab/nvidia-runtime-inspection/nvngx_dlssnr.dll'
    expected = 'e16bcf15e16e13f527491cdf7845b2fe6521a738d8f7c9c721866a8496e1fc8e'
    if hashlib.sha256(runtime.read_bytes()).hexdigest() != expected:
        raise RuntimeError('NVIDIA runtime differs from the tested signed RTX 50 runtime')
    for src, name in [(SOURCE/'x64/Release/OptiScaler.dll','winmm.dll'),
                      (SOURCE/'x64/Release/a/nvngx.dll_dlssnr.dll','nvngx.dll_dlssnr.dll'),
                      (runtime,'nvngx_dlssnr.dll')]:shutil.copy2(src, DEST/name)
    config=configparser.ConfigParser(interpolation=None,strict=False)
    config.optionxform=str
    config.read(SOURCE/'OptiScaler.ini')
    updates={
        'Upscalers':{'VulkanUpscaler':'dlss'},
        'FrameGen':{'Enabled':'false','External':'true'},
        'DLSSG':{'AdaMfgUnlock':'false','AmpereMfgUnlock':'false'},
        'Menu':{'OverlayMenu':'false','ShortcutKey':'-1'},
        'Spoofing':{'StreamlineSpoofing':'false','Dxgi':'false','Vulkan':'false','VulkanExtensionSpoofing':'false','SpoofHAGS':'false'},
        'Plugins':{'LoadReshade':'false','LoadAsiPlugins':'false','LoadSpecialK':'false'},
        'Log':{'LogToFile':'true','LogLevel':'2','LogAsync':'false','OpenConsole':'false'},
        'DlssNr':{'Enabled':'false','ToggleKey':'-1','RunBeforeSR':'false','FinishedPicture':'false','AutoCapture':'false','Passes':'1','Precision':'0'}}
    for section, values in updates.items():
        if not config.has_section(section):config.add_section(section)
        for key,value in values.items():config.set(section,key,value)
    with (DEST/'OptiScaler.ini').open('w') as stream:config.write(stream,space_around_delimiters=False)
    redist=Path('C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Redist/MSVC/14.44.35112/x64/Microsoft.VC143.CRT')
    for name in native_neural.FILES[4:]:shutil.copy2(redist/name,DEST/name)
    names=native_neural.FILES
    manifest=dict(schema=1,private_local_validation_only=True,backend_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip(),
                  files={name:hashlib.sha256((DEST/name).read_bytes()).hexdigest() for name in names})
    (DEST/'manifest.json').write_text(json.dumps(manifest,indent=2))
    shutil.copy2(SOURCE/'LICENSE',DEST/'OptiScaler-LICENSE.txt')
    shutil.copy2(SOURCE/'Licenses/RenoDX_ATTRIBUTION.txt',DEST/'RenoDX-ATTRIBUTION.txt')
    (DEST/'PRIVATE-TEST-BUILD.txt').write_text(
        'Private local validation build. Not approved for public redistribution.\n'
        'Includes the user-supplied NVIDIA 310.8 runtime and a modified GPL OptiScaler backend.\n'
        'Native Vulkan rendering in Endfield remains unverified. No ReShade dependency.\n'
        'The app installer stages components only. Use Set up neural rendering with the game closed.\n'
        'Enable DLSS in Endfield, then choose Check status. NR begins off. Insert toggles NR.\n'
        'Use Remove neural rendering with the game closed to restore the original files.\n'
        'The native source, pinned dependencies and integration are included below.\n')
    subprocess.run(['git','archive','--format=zip','--output='+str(DEST/'OptiScaler-upstream-source.zip'),'HEAD'],cwd=SOURCE,check=True)
    patch=subprocess.check_output(['git','diff','--','OptiScaler/dlssnr/DlssNrFeature_Vk.cpp','OptiScaler/proxies/NVNGX_Proxy.h','OptiScaler/dllmain.cpp'],cwd=SOURCE)
    (DEST/'fate-vulkan-control.patch').write_bytes(patch)
    with zipfile.ZipFile(DEST/'Fate-native-control-source.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for path in (ROOT/'native/nr-control').iterdir():archive.write(path,'native/nr-control/'+path.name)
        archive.write(ROOT/'tools/build_native_nr.py','tools/build_native_nr.py')
    (DEST/'submodule-revisions.txt').write_bytes(subprocess.check_output(['git','submodule','status'],cwd=SOURCE))
    print('Private native payload staged: '+str(DEST))

if __name__=='__main__':main()
