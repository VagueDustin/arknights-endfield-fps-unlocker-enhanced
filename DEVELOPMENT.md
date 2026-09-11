# Fork development status

Current milestone: read-only compatibility inspection. No repaired binary has
been built or validated in game. Upstream binaries remain historical artifacts.

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
including all seven APIs used by the legacy FPS code. No legacy unlocker loader
files were present. The runtime SHA-256 was
`db7e920698e3c4a375d85fd42c3ffcc03fa551f611b8ba9a3528b296079d9947`.

## Proposed implementation sequence

1. Establish a reproducible source build and an FPS-only component with complete
   API validation, bounded initialization retries, and useful failure logs.
2. Replace the installer with explicit game-directory selection, file ownership
   checks, backups, transactional installation, and exact restoration. The game
   already supplies d3dcompiler_47.dll; blindly overwriting it is unacceptable.
3. Validate FPS behavior and frame pacing in gameplay and across zone changes.
4. Add FPS presets, independent VSync control, and an optional background cap.
5. Add per-feature graphics compatibility checks before exposing AA, shadow,
   ambient occlusion, or resolution controls. Unknown builds must not receive
   hardcoded graphics writes by default.

The legacy FPS component also includes file-hiding hooks and a worker that calls
IL2CPP without attaching that worker to its domain. Those behaviors need review
before producing a new runtime build. The graphics component uses hardcoded
field offsets and custom trampoline code; export availability does not validate
either. Crash reports are useful leads, not a reproduction on this installation.
