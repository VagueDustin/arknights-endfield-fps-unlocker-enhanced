# Fork development status

Current milestone: compiled experimental FPS runtime and standalone desktop/CLI
manager. The Windows CI build and native integration test passed at revision
`b857401`. A local install completed with matching hashes and an intact compiler
backup. Gameplay validation is pending. Upstream binaries remain historical artifacts.

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
3. Pending: actual launch, measured FPS, frame pacing, focus changes, zone changes,
   extended gameplay, renderer-specific loader behavior, and real-game restore.
4. Implemented: desktop/CLI managers, presets, live configuration, VSync control,
   background cap, and Epic folder discovery. Python is bundled in standalone EXEs.
5. Pending: individually validated graphics controls. The UI explicitly marks them
   disabled; no legacy graphics DLL is built or installed.

The modern FPS component omits the legacy file-hiding hooks and attaches its
worker before IL2CPP calls. The worker still invokes Unity setters outside the
game's main thread; the fake runtime test cannot establish that the current
Unity player permits these calls. This needs explicit gameplay validation or a
verified main-thread dispatch path before any stable-release claim.
The legacy graphics component uses hardcoded
field offsets and custom trampoline code; export availability does not validate
either. Crash reports are useful leads, not a reproduction on this installation.
