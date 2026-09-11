# UI refinement and runtime compatibility

The neural-rendering page now follows setup, launch, and picture adjustment. It checks installation on opening the app, displays native results in its own readable status card, and keeps the picture action visible in the footer. Advanced model controls and older ReShade tools are collapsed by default.

The three primary picture controls are enabled state, style, and strength. Renderer status refreshes in the background. Current values can populate untouched controls, while unsaved edits are preserved and labelled as not applied. Picture changes require a responding renderer. Setup and removal require the game to be closed. Preview mode disables writes.

FPS actions appear only on Performance and Graphics. Recovery explicitly covers the FPS unlocker, and neural results no longer populate its output. Buttons distinguish setup, update, saving with the game closed, and applying while running.

Existing Microsoft runtime DLLs no longer block native setup. Identical or newer versions are reused without taking ownership. Older versions are backed up in the recovery journal before upgrade and restored byte-for-byte on removal. Unknown versions fail before modification. Changed installed files and corrupt backups still block removal.

Validation completed locally:

- 59 regression tests, including older/newer/identical runtimes and corrupt backups.
- Installation and restoration using copies of the actual game's four 14.29 runtime DLLs, with exact original-byte verification.
- Visual inspection of Performance, Graphics, neural rendering, advanced expand/collapse, and FPS Recovery.
- Hidden UI checks for page-specific actions, renderer value synchronization, preservation of edits, result-panel separation, and preview write protection.

Native rendering in Endfield remains a separate uncompleted game test. No game files were changed during this UI review.
