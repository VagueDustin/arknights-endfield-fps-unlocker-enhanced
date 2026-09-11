# DLSS 5 setup in Fate Engine

The DLSS 5 panel imports the exact three components used in the successful Endfield test. The bundled 0.4.4 release includes them; source-only builds prompt for a component folder. This integration manages game-local addon files; ReShade is a separate prerequisite.

## Prepare

1. Close Endfield.
2. Install **ReShade 6.8.0 with full addon support** from [ReShade](https://reshade.me/) for `Endfield.exe`, choosing Vulkan. Use the official installer for this step and for later ReShade removal. Fate Engine checks the 64-bit layer registration and Endfield's enabled-app entry.
3. Obtain the tested files from their original providers and place these three files together in one folder:

| File | Tested version | SHA-256 |
| --- | --- | --- |
| `renodx-dlss5.addon64` | Krish v4.55 / 0.2026.0828.0517 | `9150097cdee2953cdc9894d2e5606ea5100e6c8f95fc7bb1b407328b4391a07a` |
| `dlss5-bridge.addon64` | 1.4.13-pre6 | `11278e8afbcf81cd545e64d0fe8339ae830f5636d33fa998554076a96eef8a93` |
| `nvngx_dlssnr.dll` | 310.8.0.0 | `e16bcf15e16e13f527491cdf7845b2fe6521a738d8f7c9c721866a8496e1fc8e` |

The original addon post is in [the author's Discord thread](https://discord.com/channels/1408098019194310818/1543802634991968366/1543802804668465292). The bridge is published by [NIGos](https://github.com/NIGos/dlss5-bridge/releases/tag/v1.4.13-pre6). No public distribution source for the exact NVIDIA runtime is supplied here; use an authorized copy. A signed DLL or an available download does not establish redistribution rights.

The newer `renodx-dlss.addon64` is not compatible with this tested package and must not be loaded alongside it. Fate Engine stops if it finds that addon or an existing target file. An external working setup remains external; it is not silently adopted.

## Install and use

Open **DLSS 5**, choose **Check setup**, then **Install DLSS components** and select the prepared folder. If Windows denies game-folder access, run Fate Engine as administrator for that file operation. The app itself does not require elevation for inspection.

Existing ReShade settings are preserved. New settings default to NR off and **Insert**. An existing custom binding or enabled state is retained. **Set toggle to Insert** under repair and removal writes the binding with the game closed and retains a backup. The CLI can also save the next-launch enabled state. Live styles and presets are controlled in ReShade.

Use Insert in game for live toggling. Home opens ReShade for the addon's styles and presets. External live appearance controls have not been validated and are not exposed in Fate Engine. The panel reports files and saved settings, not current GPU execution or measured FPS.

## Remove and recover

**Remove DLSS components** removes only the files installed by this feature. Changed DLLs or bridge configuration stop removal. A ReShade config modified since installation is preserved; otherwise its original bytes are restored. ReShade, its logs, and native game DLSS/Streamline libraries remain untouched. Recovery journals and settings backups remain in the game folder.

The journal is written before installing components. A failed copy triggers rollback; an interrupted process can be recovered with **Remove DLSS components**. App uninstall also restores recorded managed DLSS installations and stops if the game is running or recovery cannot complete.

## Distribution decision

- The bridge publishes an [MIT license](https://github.com/NIGos/dlss5-bridge/blob/main/LICENSE).
- ReShade publishes [source and binary redistribution conditions](https://github.com/crosire/reshade/blob/main/LICENSE.md).
- The public [Streamline license](https://github.com/NVIDIA-RTX/Streamline/blob/main/license.txt) does not by itself establish the rights for the separately supplied NR binary.
- The project maintainer confirmed permission to distribute the tested full bundle for release 0.4.4. Their original rights and terms remain in effect.

Successful neural-only gameplay has been observed. Combined FPS-runtime/NR operation, other hardware, and extended stability still require validation.

## CLI

```powershell
.\EndfieldManager.exe neural-inspect --game 'C:\path\to\EndField Game'
.\EndfieldManager.exe neural-install --game 'C:\path\to\EndField Game' --package 'C:\path\to\components'
.\EndfieldManager.exe neural-enable --game 'C:\path\to\EndField Game'
.\EndfieldManager.exe neural-insert --game 'C:\path\to\EndField Game'
.\EndfieldManager.exe neural-restore --game 'C:\path\to\EndField Game'
```
