# DLSS 5 with ReShade

Fate Engine manages the FPS unlocker and the tested neural components. ReShade provides the in-game DLSS 5 controls. The native OptiScaler prototype is no longer offered in the app because it failed Endfield startup testing.

## Setup

1. Close Endfield. Open Fate Engine and select the folder containing Endfield.exe.
2. On the DLSS 5 page, select **Open ReShade setup**. The bundled installer includes ReShade 6.8.0 with full addon support. Other packages open the official download page: https://reshade.me/.
3. Complete the official setup wizard for Endfield.exe using **Vulkan**. Allow its administrator prompt if required. Additional shader packs are optional for this neural setup.
4. Return to Fate Engine and select **Install DLSS components**. The bundled release supplies the tested files. Other packages ask for a folder containing your own copies. Fate Engine checks their hashes before installation.
5. Select **Check setup**, then launch Endfield through Epic. Enable DLSS in the game's graphics settings.

## In-game controls

- **Home:** open ReShade. Finish or skip its first-run tutorial, then find the RenoDX DLSS 5 controls for styles, presets, and strength. Press Home again to close it.
- **Insert:** toggle neural rendering. Fresh setups start with NR off. Existing settings are preserved.
- Compare the same scene with NR on and off. The user's earlier test measured approximately 110 FPS off and 50 FPS on; this is an example, not a performance guarantee. The open overlay can also reduce FPS.

The app checks installed files and saved settings. It does not claim to measure active NR rendering. Styles and presets are adjusted in ReShade, not in Fate Engine.

## Tested components

- ReShade 6.8.0, full addon build
- renodx-dlss5.addon64, v4.55
- dlss5-bridge.addon64, v1.4.13-pre6
- nvngx_dlssnr.dll, 310.8.0.0

Do not combine renodx-dlss5.addon64 with renodx-dlss.addon64. Do not reinstall the failed native prototype alongside this setup.

## Removal

Close Endfield. In Fate Engine, expand **repair and removal** and select **Remove DLSS components**. User-edited ReShade settings are preserved. To remove ReShade itself, run its setup wizard for the same game and choose Uninstall. Fate Engine does not delete shared Vulkan registration used by other games. FPS unlocker removal is separate under Recovery.

## Distribution

The bundled 0.4.4 release includes the tested components with their original attribution. The project maintainer confirmed permission to distribute the full bundle. Third-party components retain their owners' licenses and rights; Fate Engine's MIT license does not relicense them. This is an experimental community tool, not an official NVIDIA, ReShade, or game-publisher product.

Source/CI builds without the bundled components open the official ReShade download page and prompt for the user's component folder.
