# Native neural rendering integration audit

Status: experimental backend selection, not a working native integration.
Date: September 11, 2026.

## Required result

Fate Engine should install a reproducible NR setup and control it from its own desktop panel. An applied setting must be acknowledged by the rendering backend, with failures visible in the app. ReShade-free operation is preferred. Existing game libraries and the restored clean game installation must remain intact while the prototype is developed.

## Findings

### Existing tested stack

The tested `renodx-dlss5.addon64` has only `NAME` and `DESCRIPTION` exports. Its strings reference ReShade registration, event, configuration, and overlay APIs, plus `NRPreset`, `NRStyle`, and other settings. This does not expose a public external settings API. An INI key's presence does not establish that the addon rereads it during gameplay.

The tested bridge source was inspected at commit `cff6cf4da7b084dae3f870fcc60e0ef019c32944` (v1.4.13-pre6). `RegisterWithReShade` in `src/dlss5-bridge.cpp` locates the ReShade host. `VkmRegisterEvents` in `src/vkmirror.inc` uses its runtime, command-list, and device lifecycle events. Removing the overlay does not remove these dependencies. [Pinned source](https://github.com/NIGos/dlss5-bridge/tree/cff6cf4da7b084dae3f870fcc60e0ef019c32944)

### Direct native candidate

The OptiScaler NR fork was inspected at commit `e237f895623742b761f9e5f00067cb3dc62619f4`. It has a Vulkan NR feature implementation (`OptiScaler/dlssnr/DlssNrFeature_Vk.cpp`) as well as D3D12 code. Its in-process menu updates style, intensity, tone, structure, and related settings. Its documentation lists the exact signed RTX 50 runtime hash previously tested on this machine. These facts make it a candidate for testing, not evidence of Endfield compatibility or an external control channel. [Pinned source](https://github.com/wilsjo2/OptiScaler-DLSSNR-PreSR-Multipass/tree/e237f895623742b761f9e5f00067cb3dc62619f4)

The candidate is GPL-3.0 licensed and includes other attributions. Do not copy its implementation into MIT-labelled Fate Engine code. A separately maintained GPL backend would need its own corresponding source, build instructions, license notices, and distribution review. IPC separation alone is not a blanket legal conclusion about a combined distribution.

Its menu labels numbered presets as experimental hints with unverified visual effect. Styles are separate controls. Preserve that distinction rather than inferring quality levels from preset numbers.

An MIT-licensed image/video NR implementation also exists, but an offline D3D12 image pipeline does not provide Endfield's Vulkan input capture, synchronization, or output composition. It was inspected as a reference only and not copied or executed. [Source](https://github.com/DaniilSokolyuk/video2dlssnr)

### NVIDIA distribution and SDK

Live recursive tree checks of NVIDIA/DLSS and NVIDIA-RTX/Streamline found no paths containing `dlssnr`, `dlss_nr`, or `neural` at the audit time. That is a scoped observation, not proof no partner SDK exists. The user-supplied 14-entry runtime archive contained no license, EULA, notice, or README files. Its NVIDIA signature proves provenance, not redistribution permission.

The OptiScaler candidate likewise requires the NVIDIA runtime separately. The fully bundled installer requirement therefore remains unresolved. Do not include that runtime in a public build until its applicable distribution terms are established.

## Chosen prototype direction

Evaluate the separately licensed native Vulkan backend before writing a replacement for ReShade's full API. Keep the existing RenoDX/ReShade stack as a known test reference. No prototype is installed into the restored game yet.

1. Build and test the pinned backend in isolation, retaining upstream licensing and notices. MSVC v143 and the Windows SDK are now installed; the modified native DLL and forwarder compile successfully.
2. Verify one default NR evaluation with the signed runtime, then test Endfield Vulkan inputs and composition. Do not equate successful DLL loading with neural output.
3. Add an explicit backend control endpoint owned by the current user. Avoid arbitrary memory writes and simulated overlay input.
4. Send versioned requests with a session ID and monotonically increasing revision. Validate known options and finite numeric ranges; enqueue changes to the render thread. Return the applied revision, actual settings, and any model recreation failure. Report a pending update until the render thread acknowledges it.
5. Commit expensive setting changes when a slider is released, rather than recreating a model on every mouse movement. Keep the last successful settings if recreation fails. Report hotkey changes back to the app.
6. Test startup, setting changes, device/feature resets, resolution changes, process exit, and coexistence with the FPS runtime. Then test install/restore against a clean game directory.

Only after these checks should the app replace its current next-launch controls with live controls. Do not publish an all-in-one claim while the renderer or redistribution question is unresolved.

## Private prototype build

The local private installer now contains the compiled Vulkan backend, forwarder, user-supplied signed RTX 50 runtime, disabled-by-default configuration, and source/notices. A separate experimental app section provides live enable, style, preset, intensity, structure, tone, skin and automatic mask controls. No ReShade host is required by this native path.

The shared-memory transport has passed a compiled C++ probe for acknowledgement, exact settings readback, disable, malformed-request rejection, and prevention of false rendered status. The 55 Python tests pass, including install/restore, partial rollback, package integrity and external-file preservation. These checks do not establish Endfield rendering compatibility.

Remaining game validation includes NR feature creation, GPU synchronization, visual output, changing settings, Insert, device resets and coexistence with the FPS runtime. The upstream backend can stop NR after a model creation failure; automatic restoration of the previous model is not implemented. Accepted settings must not be described as successful rendering. No prototype has been installed into the restored game.

## Reproducible evidence

`tools/audit_neural_interfaces.py` parses the binaries without executing them. `docs/neural-interface-audit.json` records hashes, exports, ReShade references, and setting-name evidence for the exact local binaries. Third-party source checkouts stay under ignored `build/native-nr-audit`; none is copied into Fate Engine's MIT source.

## Source location

The GPL-3.0 headers, probes, build script, and packaging script for this prototype are kept on the `experiments/native-nr` branch, separate from the MIT-licensed main tree. The audit tool `tools/audit_neural_interfaces.py` and `docs/neural-interface-audit.json` stay on main because they only inspect binaries.
