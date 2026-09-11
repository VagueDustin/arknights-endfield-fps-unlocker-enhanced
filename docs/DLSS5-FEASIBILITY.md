# DLSS 5 feasibility - September 11, 2026

DLSS 5 is a real potential extension, but is not integrated into this app. The local machine reports an RTX 5070 with driver 616.92. NVIDIA's published DLSS 5 launch targets RTX 50-series hardware; that is a hardware-family match, not proof that this game and driver combination will work. [NVIDIA announcement](https://www.nvidia.com/en-eu/geforce/news/dlss-5-3d-guided-neural-rendering/)

The experimental dlss5-bridge project reports Endfield success with DLAA, multi-frame generation, and neural rendering in its 1.4.13 prerelease series. It also documents unresolved performance issues. Its integration uses ReShade and a compatible neural rendering addon/model, bridging native graphics inputs into a D3D12 session. Some bridge settings reload, but Vulkan session behavior and launch-only options limit live changes. Neural appearance controls belong to the addon, so a supported control interface must be established before promising sliders in our app. [Maintainer documentation](https://github.com/NIGos/dlss5-bridge)

## Proposed implementation sequence

1. Identify Endfield's active rendering backend and verify the exact bridge/addon/model versions and distribution permissions from their original maintainers.
2. Run an opt-in, reversible compatibility experiment alongside the existing FPS runtime. Record startup, image quality, frame time, GPU memory use, stability, and restoration results.
3. Identify supported external controls. Label each option accurately as live, session reset, or restart required. Do not silently patch unknown settings or present unsupported controls.
4. If the experiment succeeds, add a separate Neural Rendering page with readiness checks, enable/restore, presets, and supported appearance settings. Keep original game graphics controls independently usable.

No neural addon, model, or bridge has been installed as part of this UI redesign. Official engine integration would require developer integration work; an external UI alone cannot supply the necessary rendering inputs. Performance and compatibility remain unverified on this machine.

## Local prerequisite check

The latest local Player.log, written September 11 at 04:42, identifies Vulkan and RTX 5070. This is the latest recorded session, not a running-game observation. Installed DLSS SR/FG DLL versions are 310.5.2.0, and Streamline is 2.10.3.0. Those versions match a reported successful configuration, but that report used a different GPU and the CN client. [Endfield test discussion](https://github.com/NIGos/dlss5-bridge/issues/27)

Bridge v1.4.13-pre6 is staged in the ignored `build/dlss5-lab` folder. Its SHA-256 matches the official release digest: `11278e8afbcf81cd545e64d0fe8339ae830f5636d33fa998554076a96eef8a93`. ReShade 6.8.0 with full addon support is also downloaded from its official site, but has not been executed. Its signer thumbprint matches the published ReShade thumbprint; Windows reports an untrusted certificate root, so this is not a successful Windows certificate-chain validation.

The matching `renodx-dlss5.addon64` and `nvngx_dlssnr.dll` remain missing. The maintainer-linked Discord package was requested from the user; no unofficial mirror package was substituted. Neither ReShade nor the bridge is currently installed. No Endfield process was running at the check, and the existing FPS runtime was absent with restoration backup folders present. Preserve that state until preparing the complete test, and explicitly distinguish neural-only validation from coexistence testing with the FPS runtime.

Once the package is available, inspect its provenance and configuration interface, prepare an exact file/registry rollback inventory, then install the Vulkan integration and test a launch. Neural on/off comparisons must include frame times and visual output, not just an addon reporting active. Keep all publishing on hold until testing and user approval.

The user supplied the official RenoDX releases page. Both `snapshot` and `nightly-20260911` were checked through GitHub's release API: their DLSS assets are `renodx-dlssfix.addon32`, `renodx-dlssfix.addon64`, and debug symbols. They do not include the required generic DLSS 5 addon or neural runtime DLL. The DLSS Fix addon and its shared hook source were inspected; this release does not replace the missing neural-rendering package. [Official releases](https://github.com/clshortfuse/renodx/releases)

## Download inspection and official integration

The user's `DLSS310.8.0-Streamline2.13.zip` has now been inspected. It contains `nvngx_dlssnr.dll` 310.8.0.0 and `sl.dlss_nr.dll` 2.13.0.0. Both extracted files have valid NVIDIA Authenticode signatures. They are staged only under the ignored `build/dlss5-lab/nvidia-runtime-inspection` folder; no game DLL was replaced. Their SHA-256 values are:

- `nvngx_dlssnr.dll`: `e16bcf15e16e13f527491cdf7845b2fe6521a738d8f7c9c721866a8496e1fc8e`
- `sl.dlss_nr.dll`: `9f6672e5e0170dc118a3188d21bda187e1fc1aa3502895b21ab846d23165c11d`

The required RenoDX neural addon is still absent from Downloads, including a recursive filename check. The NVIDIA runtime is no longer the missing prerequisite for the proposed bridge experiment.

RenoDX is an integration layer, not a replacement for NVIDIA's model. A custom Fate Engine integration could in principle invoke NVIDIA's runtime directly, but would need the feature's API contract, correct rendering inputs, synchronization, output composition, and compatibility with Endfield's existing Vulkan/Streamline integration. Dropping a new plugin beside the game does not make the game request or evaluate the feature.

At inspection time, NVIDIA's public Streamline main tree contains no `dlss_nr`, `dlssnr`, or neural-named paths; its public headers do not include a neural-rendering feature header. This does not prove partner SDK access is unavailable. The public integration guide documents explicit frame/resource tagging and feature evaluation, so the existing general API alone is not enough to assume a reliable neural integration. [NVIDIA Streamline guide](https://github.com/NVIDIA-RTX/Streamline/blob/main/docs/ProgrammingGuide.md)

## First live test: newer RenoDX addon

After explicit user approval, installed ReShade 6.8.0's Vulkan layer with only Endfield in its enabled-app list, bridge 1.4.13-pre6, NVIDIA NR 310.8.0.0, and the user-provided newer `renodx-dlss.addon64` (SHA-256 `1d855cf226857dce890cffbf7206ba9b6497ce1d471b217c1c8b44b6cd5d27e9`). Existing game DLSS/Streamline DLLs were unchanged. The accompanying screenshot states that this newer addon lacks native Vulkan support; bridge compatibility was an experiment.

At 06:45:22 on September 11 the game crashed during startup with access violation `0xC0000005`. The bridge crash recorder identifies an attempted execution at unmapped memory, called from `renodx-dlss.addon64+0xA4F6F`. ReShade logged multiple addon unload/reload cycles before the fault. This is evidence of a compatibility failure, not a definitive root-cause attribution and not a successful NR frame evaluation.

The game process exited. Logs and configuration were preserved under the ignored `build/dlss5-lab/first-launch` folder. The prepared rollback completed at 06:46:19, removing the added binaries and ReShade layer registration. The empty preset left by ReShade uninstall was removed separately after checking the absent-file baseline. A clean game launch after rollback has not yet been confirmed.

Next candidate: the older `renodx-dlss5.addon64`, preferably the 4.55 build from the successful Endfield report. Do not rename the newer addon to impersonate the older one, and never load both together. The user has been asked for the older package. No DLSS 5 UI integration or repository push is justified by this failed test.

## Second test prepared: original v4.55

Using the user's open Discord window, followed the ShortFuse post's fallback link to Krish's original DLSS5 Tool thread and downloaded the attachment from the v4.55 post dated August 30 at 19:01. [Author's post](https://discord.com/channels/1408098019194310818/1543802634991968366/1543802804668465292)

The downloaded file is 1,694,720 bytes, version `0.2026.0828.0517`, SHA-256 `9150097cdee2953cdc9894d2e5606ea5100e6c8f95fc7bb1b407328b4391a07a`. Its hash prefix matches the addon identified in the successful Endfield report. Under the existing explicit test-installation approval, it replaced the failed newer candidate in a fresh installation at 06:51:35. The newer addon is absent from the game folder. Bridge and NVIDIA runtime versions are unchanged.

Separate install/restore scripts, baseline, and checksum results are under the ignored `build/dlss5-lab-455` folder. ReShade's enabled-app list contains only Endfield. Startup and neural frame evaluation are pending for this second test.

## Second test results

Endfield reached gameplay with PID 64572 and remained responsive. At 06:52:31, the RenoDX log confirmed the signed NVIDIA NR runtime initialized, created feature 18, and successfully evaluated neural output at 2560x1440 with matching guide dimensions. Successful evaluations were reported at counts 1 and 60. The bridge subsequently reported thousands of frames delivered to the Vulkan game. Logs are preserved under `build/dlss5-lab-455/successful-launch`.

The user confirmed a visible effect and approximately 110 FPS with NR off versus 50 FPS with NR on. This is a user-observed comparison in one scene, about a 55% frame-rate reduction, not a controlled benchmark. F6 off/on transitions were independently recorded in the addon log. Frame generation coexistence and long-session stability remain untested.

An external INI edit briefly requested `NRIntensity=0.85`; no runtime setting readback confirmed uptake. The original configuration was restored while preserving other current settings. Do not claim external live slider support based solely on an INI write. The in-game toggle works; external live appearance controls still need a verified integration path. Neural rendering should be opt-in given the observed performance cost.

## Confirmed keybinding and comparison captures

The user subsequently confirmed Insert works well and requested it as the project default. The tested configuration is `NRToggleKey=45` under `[RenoDX.DLSS5]`; see [keybindings](DLSS5-KEYBINDINGS.md). F6 conflicts with an Endfield menu. The repository includes a defaults fragment at `assets/dlss5/ReShade.defaults.ini` for future integration; it is not currently installed by the app.

Fifteen user-supplied screenshots cover five off/on scenes plus NR presets 1-3, Natural, and Cinematic. The [comparison gallery](comparisons/index.html) provides a draggable divider and full-image switches. The README provides static comparisons compatible with GitHub. Capture labels come from the supplied filenames; settings, frame timing, and camera alignment were not independently recorded for each image.
