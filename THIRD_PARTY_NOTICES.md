# Third-party notices

Fate Engine is independently maintained by VagueDustin Enterprises. The root LICENSE applies to this project's contributions. Third-party contributions retain their respective notices and terms.

## Original project

Fate Engine originated from [EightySixK's Arknights Endfield FPS Unlocker](https://github.com/EightySixK/Arknights-Endfield-FPS-Unlocker). The original copyright and full MIT permission notice are preserved in [licenses/EightySixK-MIT.txt](licenses/EightySixK-MIT.txt) and accompany distributions. This attribution does not identify the original author as the owner or maintainer of Fate Engine.

Unused original source, resource files, prebuilt binaries, and vendored libraries have been removed from the current tree. Git history retains their provenance. This cleanup is not a claim that the project was developed independently of all upstream influence.

## Other dependencies

- MinHook: BSD 2-clause license, copied by the native package build into `licenses/MinHook.txt`.
- CustomTkinter and darkdetect: MIT licenses, collected from the installed distributions.
- Pillow: its included license, collected from the installed distribution.
- PyInstaller: its included license and bootloader distribution exception, collected from the installed distribution.
- Inter and Cinzel font files: their included SIL Open Font License notices under `assets/fonts`, also installed with the app.

These third-party notices do not transfer ownership of their contributions to VagueDustin Enterprises. Third-party rendering components retain their own licenses and permissions.

## Bundled ReShade setup

Bundled releases (0.4.4 and later) include the official ReShade 6.8.0 full-addon setup and the tested neural components. The project maintainer confirmed permission to distribute the full bundle. ReShade is copyright Patrick Mours and distributed under BSD 3-clause terms; its complete notice accompanies the package under licenses/ReShade-BSD-3-Clause.txt. The DLSS 5 bridge by NIGos has its MIT license included separately. The Krish v4.55 RenoDX-family addon and NVIDIA neural runtime retain their authors' rights and distribution terms. They are not relicensed under Fate Engine's MIT license. Bundling does not imply endorsement by any of those authors.
