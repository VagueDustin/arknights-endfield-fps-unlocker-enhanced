# Endfield Enhancer (experimental fork)

An FPS-only modernization of [EightySixK's unlocker](https://github.com/EightySixK/Arknights-Endfield-FPS-Unlocker).
New code lives in `src/modern`. Historical upstream binaries in `bin` are not used.
An initial gameplay test on September 11, 2026 was reported working by the user;
runtime logs also confirm foreground/background target changes. Extended stability
and other rendering modes remain unverified. This is still an experimental build.

## Features

- 120, 144, 240, and unlimited presets; custom targets from 30–1000 FPS.
- Optional background FPS cap; 0 disables the background override.
- Independent VSync control and restoration of the value captured at startup.
- Live settings reload, bounded initialization, and per-process diagnostic logs.
- Reversible installer with checksums, conflict detection, and rollback.
- Desktop panel with Epic installation detection and a command-line manager.

AA, shadows, ambient occlusion, and render-scale overrides remain disabled.
The old graphics code uses unverified offsets and is excluded from the build.

## Use the experimental package

Download the artifact from a successful **Windows build and tests** run on the
`modernize-fps` branch. Extract the entire package into its own folder. Keep the
manager next to `package.json` and the two compiled DLLs.

Run **EndfieldEnhancer.exe**, choose the folder containing `Endfield.exe`, inspect
it, and install with the game closed. Defaults: 120 FPS, VSync off, no background
override. If Windows denies write access, run the manager as administrator.

Launch through the normal game launcher. **Apply settings** updates the runtime
within approximately one second. VSync can override the FPS target. Unlimited
uses Unity's desktop value -1 with VSync off; see
[Unity's FPS documentation](https://docs.unity3d.com/ScriptReference/Application-targetFrameRate.html).

For command-line use, run EndfieldManager.exe (or `python manage.py`):

```powershell
.\EndfieldManager.exe inspect --game 'C:\path\to\EndField Game'
.\EndfieldManager.exe install --game 'C:\path\to\EndField Game' --preset high-refresh
.\EndfieldManager.exe configure --game 'C:\path\to\EndField Game' --fps 240 --background 30 --vsync 0
.\EndfieldManager.exe diagnostics --game 'C:\path\to\EndField Game'
.\EndfieldManager.exe restore --game 'C:\path\to\EndField Game'
```

Logs are in `%LOCALAPPDATA%\EndfieldEnhancer`. Diagnostics includes the latest
log; check its timestamp because it may belong to an earlier launch or test.

## Installation and recovery

The loader forwards shader compiler calls to an exact copy of the game's original
`d3dcompiler_47.dll`, preserving names and ordinals. It loads only the new FPS
component. No Vulkan proxy, legacy payload, or boot.config edit is used. The FPS
runtime only activates in a process named Endfield.exe.

Before replacement, the manager saves the original compiler and SHA-256 hashes
in `.endfield-enhancer`. The loader is installed last. Failed writes trigger
restoration. After an interrupted installation, run **restore** before retrying.
Restore refuses to overwrite DLLs changed by a game update or another tool;
preserve the backup for manual recovery. Completed restore archives the original
and last configuration in `.endfield-enhancer-restored*`.

Restore before a game update or another compiler-proxy installation. The manager
does not disable anti-cheat or conceal files. Gameplay and account safety cannot
be established by these tests; this remains an experimental game modification.

## Build and test

Requirements: Windows x64, Visual Studio C++ tools and Windows SDK, CMake 3.24+,
Git, and Python 3.11+. MinHook is built from a pinned source revision.

```powershell
python -m unittest discover -s tests -v
cmake -S . -B build -A x64
cmake --build build --config Release
ctest --test-dir build -C Release --output-on-failure
cmake --install build --config Release --prefix build/package
python tools/package_build.py build/package
```

The native harness tests real Windows compiler forwarding and a fake IL2CPP
runtime: live FPS/VSync changes, VSync restore, background cap, and attachment of
the worker thread. It does not test the real engine or its graphics API loading.
CI also builds standalone managers with PyInstaller.

## Further gameplay validation

Check startup logs, measured FPS, focus loss/return, live settings, menus,
teleporting between regions, and an extended play session. Test rendering modes
separately, then restore and verify a clean launch. Graphics overrides need
individual runtime metadata checks and gameplay tests before enabling them.

MIT license. Original copyright and attribution are preserved in LICENSE.
