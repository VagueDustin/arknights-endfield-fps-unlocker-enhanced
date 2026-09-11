# Release procedure

The 0.4.4 bundle was assembled by hand from several local build folders. This is the
repeatable procedure for the next release so the shipped runtime always matches the
tagged source, and so the release is tested the way a new user experiences it.

## 1. Prepare the source

1. Set the new version once in `assets/identity/product.json`. CMake, the runtime log,
   the installer, the executable resources, and `package.json` all read it.
2. Update `THIRD_PARTY_NOTICES.md` and the docs if bundled components changed.
3. Run `python -m unittest discover -s tests -v`. The metadata test fails if a version is
   hardcoded anywhere or the README download link is inconsistent.
4. Commit and push. Wait for **Windows build and tests** to pass on `main`.

## 2. Take the native runtime from CI

Download the `EndfieldEnhancer-windows-x64-experimental` artifact of that run. It holds
`d3dcompiler_47.dll`, `endfield_fps.dll`, `package.json`, and `licenses/MinHook.txt`
built from the exact commit. Do not copy DLLs from an older `build/package*` folder:
`tools/build_reshade_app.ps1` now refuses a runtime package whose version or hashes do
not match the current product.

A local `cmake --install build --config Release --prefix <dir>` followed by
`python tools/package_build.py <dir>` produces the same layout.

## 3. Stage the third-party payload

`python tools/package_reshade.py` copies the tested ReShade setup and the three neural
components into `build/reshade-preview/package`, verifying every SHA-256 against
`tools/neural.py` and `tools/reshade_setup.py`. The inputs stay in the ignored
`build/dlss5-lab*` folders; they are never committed.

## 4. Build the app and the bundled installer

```powershell
tools/build_reshade_app.ps1 -runtimePackage <artifact or install dir>
& <ISCC.exe> '/DPackageDir=..\build\reshade-preview\package' /DBundledReShade installer\EndfieldEnhancer.iss
tools/validate_bundled_installer.ps1 -isccPath <ISCC.exe>
```

The validation script installs an isolated copy, checks payload and runtime hashes, runs
the installed app's smoke test, and uninstalls. Without `/DBundledReShade` the installer
is named `...-unbundled.exe` and asks users for their own components; that is what CI
publishes as an artifact.

## 5. Test like a new user

On a game folder without a managed installation:

1. Install the setup executable per-user. Open Fate Engine, select the game folder.
2. **Performance > Set up FPS unlocker** with Endfield closed. The confirmation dialog
   and the Recovery page must report `installed_experimental`.
3. Launch Endfield through its launcher. Within a minute the header must show
   `GAME RUNNING`, the applied cap, and `Render loop connected`. `Runtime not detected`
   means the loader never started; stop and investigate before releasing.
4. **DLSS 5 > Open ReShade setup**, complete the wizard on Vulkan, then **Install DLSS
   components** and **Check setup**. After a launch, Check setup must report that ReShade
   initialized and loaded both add-ons; Home must open the overlay and Insert must toggle NR.
5. **Recovery > Export diagnostics** and keep the report with the release notes.
6. Remove DLSS components, remove the FPS unlocker, and confirm a clean launch.

## 6. Publish

Tag `vX.Y.Z`, attach the bundled installer and `SHA256SUMS.txt`, then update the README
download link to the new tag in a follow-up commit.
