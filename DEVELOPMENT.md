# Fork development status

Current milestone: compiled experimental FPS runtime and standalone desktop/CLI
manager. The Windows CI build and native integration test passed at revision
`b857401`. A local install completed with matching hashes and an intact compiler
backup. On September 11, 2026, the user reported that the installed build
"appears to be working perfectly." Runtime logs show repeated 30-to-144 FPS
target transitions as focus changes. This is a successful initial gameplay test;
extended stability, quantitative frame pacing, and other renderers remain unverified.
Upstream binaries remain historical artifacts.

Run with Python 3.11 or newer:

```powershell
python tools/check_compatibility.py 'C:\path\to\EndField Game'
python -m unittest discover -s tests -v
```

The checker parses the on-disk PE export table without loading or executing the
DLL. Exit code 0 means the legacy FPS API names exist, 1 means required names are
missing, and 2 means inspection failed. None of these checks establishes runtime
stability, loader compatibility, or graphics-offset validity.

The installation inspected on September 11, 2026 had 414 named runtime exports,
including all seven APIs used by the legacy FPS code and the two additional
APIs required by the modern runtime. No legacy unlocker loader
files were present. The runtime SHA-256 was
`db7e920698e3c4a375d85fd42c3ffcc03fa551f611b8ba9a3528b296079d9947`.

## Implementation status

1. Implemented: CMake/MSVC build, pinned MinHook source, checked API/hook setup,
   two-minute bounded initialization, per-process logs, attached IL2CPP worker.
2. Implemented: explicit directory selection, export/ordinal validation, checksums,
   backups, transaction journal, rollback, restore with conflict refusal.
3. Initial launch/gameplay confirmed by the user; foreground/background changes
   confirmed in runtime logs. Pending: measured frame pacing, zone transitions,
   extended gameplay, other renderers, and real-game restore.
4. Implemented: desktop/CLI managers, presets, live configuration, VSync control,
   background cap, and Epic folder discovery. Python is bundled in standalone EXEs.
5. Version 0.3.0 implements opt-in graphics controls via a before-render callback,
   with an exact runtime hash gate, typed APIs, readback, per-feature failure
   isolation, and reset. The legacy graphics DLL remains excluded. Native fake
   runtime tests pass; actual game callback and feature effects still need testing.

The modern FPS component omits the legacy file-hiding hooks and attaches its
worker before IL2CPP calls. The worker still invokes Unity setters outside the
game's main thread; the fake runtime test cannot establish that the current
Unity player permits these calls. Initial user gameplay is successful; extended
testing or moving FPS application to a verified main-thread path remains desirable.
The legacy graphics component uses hardcoded
field offsets and custom trampoline code; export availability does not validate
either. Crash reports are useful leads, not a reproduction on this installation.

## Graphics investigation

The installed metadata is version 29 with 92-byte type records, differing from
the standard 88-byte layout. The read-only inspector derives record size from
image type ranges and validates type tokens and method ownership. It successfully
read 58,110 declarations from the installed file. It does not load game DLLs,
read process memory, compute runtime field offsets, or alter graphics settings.

Current declarations include HGSettingParameters getters for rendering scale,
shadow-map resolutions, GTAO quality, TAAU, and sharpening. SettingParameter<T>
exposes Override, OverrideWithString, ChangeParamValue, and RefreshInternal.
HGSMAA exposes SetSMAAMode. These are candidates for using the game's own update
methods instead of raw backing-field writes; their behavior is not established
by declarations. Runtime generic types, value constraints, change notifications,
and exact reset behavior must be validated before using them.

Unity Application.InvokeOnBeforeRender was present but did not fire in gameplay.
Graphics dispatch now uses RenderPipelineManager.DoRenderLoop_Internal with
three validated arguments: RenderPipelineAsset, IntPtr, and UnityEngine.Object. Its signature is validated before
hooking; execution is logged and bound to the first callback thread. No callback
means no graphics writes. Each parameter is resolved independently and retained
with a GC handle while overridden. Values are captured and read back through
typed getters; OverrideWithString and MarkFeatureDirty request updates. Reset
restores a preexisting override, or invokes the game's Reset and MarkFeatureDirty
methods to return control to game settings. Actual engine behavior still needs
per-feature verification. The known-working FPS-only artifact remains available
in build/package and the upgrade manager archives installed DLLs before replacing them.

Run the inspector on the game's Endfield_Data/il2cpp_data/Metadata/global-metadata.dat:

```powershell
python tools/inspect_graphics_metadata.py 'C:\path\to\global-metadata.dat' --type HGSettingParameters
```

Raw inspection results remain in ignored local-reports. Do not commit or upload
the game's metadata or runtime binaries.

## Desktop development

Install customtkinter==5.2.2 and Pillow, then run `python tools/desktop.py`.
The theme snapshot and bundled OFL fonts live in assets/. Product colors resolve
semantic roles from brand.json. The app uses the existing locked manager for
mutations; its background status watcher only reads process IDs and bounded log tails.
Run `python tools/desktop.py --smoke-test` for a startup check. CI builds the
standalone executable and Inno Setup installer, including font and library notices.
