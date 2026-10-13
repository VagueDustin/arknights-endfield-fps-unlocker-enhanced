# AGENTS.md

Guidance for coding agents working in this repository. CONTRIBUTING.md, DEVELOPMENT.md and
docs/RELEASE.md are the full references.

## What this is

Fate Engine is a Windows x64 FPS unlocker and experimental graphics tuner for Arknights: Endfield.
Two parts:

- **Native runtime** (C++17, CMake, MSVC, MinHook from a pinned commit): `d3dcompiler_47.dll` is a
  forwarding loader and `endfield_fps.dll` the runtime that hooks the game.
- **Python tooling** (3.11+): the CLI manager (`tools/manage.py`), the customtkinter desktop app
  (`tools/desktop.py`), install/backup/restore logic, ReShade and DLSS 5 component setup, packaging.

## Layout

- `src/modern/` - the current native implementation (`loader.cpp`, `runtime.cpp`, `graphics.cpp`,
  `compiler.def`). Unused upstream source and binaries exist only in Git history.
- `tools/` - Python manager, desktop app and packaging/inspection scripts.
- `tests/` - Python `unittest` suites; `tests/native/` - C++ harness with a fake IL2CPP runtime.
- `assets/` - brand tokens (`brand.json`), fonts, icons; `assets/identity/product.json` is the
  single version source.
- `installer/EndfieldEnhancer.iss` - Inno Setup installer.
- `docs/` - setup guides, release procedure, design notes; `docs/comparisons/` is the GitHub Pages
  gallery.

## Commands

Requires Windows x64, Visual Studio C++ tools + Windows SDK, CMake 3.24+, Git and Python 3.11+.

```powershell
python -m unittest discover -s tests -v              # Python tests (CI also runs compileall on tools)
python -m compileall -q tools
cmake -S . -B build -A x64                           # fetches MinHook at the pinned commit
cmake --build build --config Release
ctest --test-dir build -C Release --output-on-failure
cmake --install build --config Release --prefix build/package
python tools/package_build.py build/package
python tools/desktop.py --smoke-test                 # needs customtkinter==5.2.2 and Pillow
python tools/check_compatibility.py '<game folder>'  # read-only export check
```

CI (`.github/workflows/build.yml`, `windows-2022`) runs all of the above, then builds the standalone
`EndfieldManager.exe` / `FateEngine.exe` with PyInstaller and the Inno Setup installer, and installs,
smoke-tests and uninstalls it.

## Rules

- Python changes: run the unittest suite. Native changes: also the MSVC build and `ctest`. Builds
  use `/W4 /WX`, so warnings are errors.
- Say plainly when a change has only automated coverage and was not validated in gameplay. The fake
  runtime does not prove behaviour in the real game; don't overstate results.
- The version lives only in `assets/identity/product.json`. `tests/test_product_metadata.py` fails
  if a version is hardcoded elsewhere or the README download link is inconsistent. Don't change the
  version unless asked; releases follow docs/RELEASE.md.
- Preserve backup ownership, integrity checks, restoration and runtime compatibility checks.
- Never commit game binaries, game metadata (`global-metadata.dat`), private data, historical
  upstream binaries or third-party runtime downloads. Local reports go in the ignored
  `local-reports/`; `build/` is ignored.
- Third-party components need documented provenance and licensing; keep `THIRD_PARTY_NOTICES.md`
  and `licenses/` current. Product colours resolve semantic roles from `assets/brand.json`.
- Redact account identifiers and personal paths from logs and examples.
- The GPL-3.0 native NR prototype lives on the `experiments/native-nr` branch, not on `main`;
  don't bring it (or its ignored tool scripts) into `main`.

## PRs

Focused changes. The PR template asks for the change, validation (game build, rendering API,
component versions for gameplay tests; separate runtime readback from visible results and
performance), and compatibility/recovery notes including any new third-party dependency and its
licence. Commit subjects are short and imperative ("Detect every Endfield install and warn when the
wrong one is managed").
