# Fate Engine: local design review

Approved name: **Fate Engine - Arknights Endfield FPS Unlocker**. Publisher: VagueDustin Enterprises. Source publication was approved September 11, 2026; this document records the local review before publication. Naming is centralized in `assets/identity/product.json`.

## Changes

- Inter bold headings replace the ornate display typography.
- Navy and gold control center with Performance, Graphics, and Recovery navigation.
- Original imagegen F emblem in the app header, Windows executable resources, window icon, Start menu shortcut, desktop shortcut, and installer.
- Searchable shortcut filename contains both Arknights and Endfield FPS Unlocker; Windows indexing still needs verification after installation.
- Custom dark installer with generated portrait artwork, company branding, and installation scope choice.

## Installation choices

| Scope | Default folder | Elevation |
| --- | --- | --- |
| Current user (recommended) | `%LOCALAPPDATA%\Programs\VagueDustin Enterprises\Fate Engine` | No admin for app installation |
| All users | `C:\Program Files\VagueDustin Enterprises\Fate Engine` | Admin for installation and updates |

The app runs with normal user permissions. Writing to the game's installation directory is a separate permission requirement. Program Files permissions are not weakened. Existing desktop preferences and runtime logs retain their EndfieldEnhancer data directory for compatibility.

The installer retains the existing application ID for same-scope upgrades and removes the old shortcut in the selected scope. Moving the installation folder can leave an old directory behind; do not run an old uninstaller to clean it up, since uninstall includes game restoration. Switching between current-user and all-users scope is not an automatic migration.

## Review artifacts and validation

- `build/fate-engine-review/package/FateEngine.exe`: local executable; use `--preview` for a review that blocks install/apply/restore actions.
- `build/installer/Fate-Engine-Arknights-Endfield-Setup-0.4.0.exe`: compiled installer.
- `build/ui-review/performance.png` and `graphics.png`: visual previews.
- 30 Python tests passed; packaged GUI startup and manager profiles passed.
- Windows product/company/version metadata verified. Installer compiled using Inno Setup 6.7.3.
- Native DLLs are the tested v0.3.2 binaries, unchanged; package integrity metadata was regenerated for this local 0.4.0 UI package.
- This review has not replaced the installed app or game files. Upgrade behavior and Windows Search indexing remain to be checked on installation. CI verifies setup, installed startup, and uninstall on each push.

See `assets/identity/GENERATION.md` for artwork prompts and `docs/DLSS5-FEASIBILITY.md` for the separate neural rendering investigation.
