"""Build the pinned, separate GPL native NR prototype without installing into a game."""
from pathlib import Path
import os
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'build/native-nr-audit/optiscaler'
PIN = 'e237f895623742b761f9e5f00067cb3dc62619f4'

def main():
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=SOURCE, text=True).strip()
    if revision != PIN:
        raise RuntimeError('Native source revision differs from the audited pin')
    for name in ('FateNrControl.h', 'OptiScalerControl.h'):
        shutil.copy2(ROOT / 'native/nr-control' / name, SOURCE / 'OptiScaler/dlssnr' / name)
    shutil.copy2(ROOT / 'native/nr-control/StartupTrace.h', SOURCE / 'OptiScaler/StartupTrace.h')
    entry = SOURCE / 'OptiScaler/dllmain.cpp'
    entry_text = entry.read_text()
    if '#include "StartupTrace.h"' not in entry_text:
        entry_text = entry_text.replace('#include "dllmain.h"', '#include "dllmain.h"\n#include "StartupTrace.h"', 1)
        marker = '        DisableThreadLibraryCalls(hModule);'
        if marker not in entry_text:raise RuntimeError('Startup trace attach point changed')
        entry_text = entry_text.replace(marker, marker + '\n        FateStartupTrace::Start(hModule);', 1)
        marker = '        spdlog::info("Init done");'
        if marker not in entry_text:raise RuntimeError('Startup trace init point changed')
        entry_text = entry_text.replace(marker, marker + '\n        FateStartupTrace::Mark("backend_init_complete\\r\\n");', 1)
        marker = 'case DLL_PROCESS_DETACH:'
        if marker not in entry_text:raise RuntimeError('Startup trace detach point changed')
        entry_text = entry_text.replace(marker, marker + '\n        FateStartupTrace::Stop();', 1)
        entry.write_text(entry_text)
    source = SOURCE / 'OptiScaler/dlssnr/DlssNrFeature_Vk.cpp'
    text = source.read_text()
    if '#include "OptiScalerControl.h"' not in text:
        text = text.replace('namespace DlssNr\n', '#include "OptiScalerControl.h"\n\nnamespace DlssNr\n', 1)
        needle = '    applied = false;\n    auto& cfg = *Config::Instance();'
        if needle not in text:
            raise RuntimeError('Vulkan control integration point changed')
        text = text.replace(needle, '    FateNrControl::Tick();\n' + needle, 1)
        if '    applied = true;' not in text:
            raise RuntimeError('Vulkan completion point changed')
        text = text.replace('    applied = true;', '    applied = true;\n    FateNrControl::Rendered();', 1)
        source.write_text(text)
    text = source.read_text().replace('FateNrControl::Tick();', 'FateNrControl::Tick(g_vk.failed);')
    source.write_text(text)
    proxy = SOURCE / 'OptiScaler/proxies/NVNGX_Proxy.h'
    proxy_text = proxy.read_text()
    marker = 'inline static void HookNgxApi(HMODULE nvngx)\n{'
    guard = '\n    // Fate diagnostic: preserve the driver\'s real capability result.\n    LOG_INFO("Fate native profile: preserving NVIDIA feature requirements");\n    return;\n'
    if 'Fate diagnostic: preserve' not in proxy_text:
        if marker not in proxy_text:raise RuntimeError('NGX diagnostic integration point changed')
        proxy.write_text(proxy_text.replace(marker,marker+guard,1))
    env = {key.upper(): value for key, value in os.environ.items()}
    msbuild = Path(os.environ['ProgramFiles(x86)']) / 'Microsoft Visual Studio/2022/BuildTools/MSBuild/Current/Bin/MSBuild.exe'
    # Serial MSBuild avoids the duplicate PATH/path environment bug in worker nodes.
    with (SOURCE / 'fate-native-build.log').open('w') as log:
        subprocess.run([str(msbuild), 'OptiScaler.sln', '/m:1', '/nodeReuse:false',
                        '/p:Configuration=Release', '/p:Platform=x64',
                        '/p:PostBuildEventUseInBuild=false', '/verbosity:minimal'],
                       cwd=SOURCE, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    print('Native build completed: ' + str(SOURCE / 'x64/Release/OptiScaler.dll'))

if __name__ == '__main__': main()
