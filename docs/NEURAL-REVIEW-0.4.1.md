# Fate Engine 0.4.1 local review

This build adds a DLSS 5 page and CLI operations for file inspection, importing three exact user-supplied components, next-launch enable/disable, Insert binding, and managed removal. ReShade installation remains a separate official-installer prerequisite. No third-party NR binaries are bundled.

Validation: 45 Python tests including 15 neural lifecycle tests; packaged desktop startup; packaged CLI inspection of the existing real-game setup; Inno Setup installer compilation. Existing native FPS DLLs are reused unchanged from the tested build. The current game setup remains externally managed and was not modified.

The read-only CLI confirmed all three real components match the tested hashes, ReShade is registered for Endfield, and the saved binding is Insert. The GUI preview was launched, but automated visual capture was blocked by a Computer Use approval timeout; visual layout review is outstanding. The 0.4.1 installer has not been installed over the user's app, and combined FPS/NR gameplay remains untested.

Local artifacts: `build/neural-review/package/FateEngine.exe`, matching `EndfieldManager.exe`, and `build/installer/Fate-Engine-Arknights-Endfield-Setup-0.4.1.exe`. Launch the app with `--preview` for read-only review. These new changes have not been pushed.
