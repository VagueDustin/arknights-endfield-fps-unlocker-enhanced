# Native Endfield startup failure

2026-09-11: The user tested private build 0.4.3. Endfield reached menu loading and exited with a warning naming winmm.dll. No OptiScaler.log or matching Application Error/WER event was found. Player.log reached Vulkan initialization and asset loading without a recorded exception. Root cause is not established; do not label this an anti-cheat rejection without further evidence.

The native installation journal and configuration were archived under build/native-crash-20260911-115159. The managed native payload was removed through its journal. All four pre-existing Microsoft runtime DLLs were restored and their original hashes verified. FPS unlocker files and settings were preserved. The user confirmed that Endfield launches normally after restoration.

This native build failed its first Endfield compatibility test. Compilation, transport tests, and installer tests did not establish game compatibility. Do not recommend reinstalling 0.4.3 native NR or publish it as working. The previously tested ReShade path remains the known reference, not proof that its components are currently installed.

## Isolated loader diagnostic

The same packaged backend and runtime dependencies passed a separate diagnostic process: LoadLibrary, timeGetTime forwarding (108 ms measured over a 100 ms sleep), Vulkan instance creation, Vulkan device creation/destruction, and process shutdown. Exit code was zero. The log confirms OptiScaler initialization and interception of Vulkan device creation. Evidence is in build/native-loader-test/result.json and loader-test.log. This does not exercise Endfield, Streamline integration, a swapchain, or NR evaluation.

The previous absence of an OptiScaler log is not evidence that initialization never ran: the supplied INI used LogToFile=auto, and the upstream default is false. The diagnostic explicitly enabled synchronous file logging. A future controlled game reproduction needs that logging before the failure can be localized. No game modifications were made for the isolated diagnostics.

## Logged game reproduction

The user reproduced the same warning with NR disabled and synchronous logging enabled. The log confirms initialization completed. Its final line is `Hooked_Vulkan_GetFeatureRequirements Spoofing support!`. This identifies the last observed call, not the faulting instruction. The test was collected under build/native-diagnostic/capture-20260911-120027 and rolled back immediately.

Inspection found unconditional feature-requirement overrides in the upstream NGX proxy, separate from the visible GPU spoofing settings. The next diagnostic variant skips registration of these overrides and preserves NVIDIA's original capability reports. This is a single-variable isolation test, not a claimed crash fix.

## Capability override isolation result

The variant preserving NVIDIA feature requirements passed the standalone loader and Vulkan device probe (exit 0, 103 ms timer delta). Its log confirmed the override hooks were skipped. Endfield still showed the same warning with NR off. Evidence: build/native-diagnostic/capture-20260911-120538. Initialization completed; no NR evaluation or explicit fault was recorded. Disabling the capability override is not a sufficient fix. No matching Application Error/WER event was found for this attempt.

The diagnostic was removed using its validated recovery journal and Microsoft runtime originals restored. FPS settings were preserved. Do not ask the user to repeat this unchanged test or reinstall the native release. Next investigation should obtain an actual fault location or compare the backend startup integration with the previously working ReShade host. A last log line alone does not justify further speculative hook changes.

## Post-uninstall verification and host comparison

After the user uninstalled, read-only inspection found no winmm.dll, OptiScaler.ini, native NR journal, or active FPS installation journal in the game directory. The diagnostic log and earlier recovery directories remain. Existing NVIDIA game DLSS files were left unchanged.

Windows CrashDumps contains five Endfield dumps from 03:18 through 06:45 on September 11. None corresponds to the 11:59 or 12:04 native diagnostic runs. Archived WER reports likewise do not establish the fault location for those runs. Do not attribute earlier dump stacks to this failure.

The pinned bridge source documents and implements a ReShade-hosted Vulkan-to-private-D3D12 mirror. It does not itself implement neural rendering or expose the separate RenoDX addon's NR preset setters. Its DllMain initializes locks and registers with ReShade; the native prototype instead initializes multiple graphics proxies and hooks. These architectural differences are candidates for investigation, not proof of the failing operation.

Next useful native test must capture a fault location or explicit failure reason before changing more hooks. Do not repeat the same launch or rename the proxy to hide it. The fallback would keep the previously working ReShade host and add a supported live-control interface to the neural consumer; changing the bridge alone or editing an INI does not establish live preset control. No fallback was installed or promised as complete.

## Opt-in exception recorder

Added StartupTrace.h to the diagnostic backend. It observes selected first-chance exceptions without changing their disposition, recording code, thread, module filename, and offset. It records attach/init/detach markers. Logging is capped and enabled only by the diagnostic INI. A first-chance record is not proof of an unhandled fault, and explicit termination or fail-fast may bypass it.

The isolated exception probe passed with diagnostics disabled and enabled: the application's handler received its deliberately raised access violation in both cases. The packaged backend also passed loader/timer/Vulkan instance/device checks with recording off and on. The enabled run recorded observer_registered, backend_init_complete, and process_detach with no selected exceptions. This is instrumentation validation, not a game compatibility pass.

The diagnostic was installed with NR disabled for the next authorized game launch. The standard journal retains original runtime files for rollback. Source and tests remain local; nothing was pushed.

## First exception-recorder game test

The user reproduced the same warning. The live trace initially contained repeated first-chance exceptions at EndfieldBase.dll+0x1D6512E. The final shared trace instead contained a fresh header and Qt5WebEngineCore.dll+0x1D5F4CD without the earlier initialization marker. The shared filename could be overwritten by another process loading the same proxy. Neither observation establishes the terminating fault. The game was restored through its journal; captures are under build/native-diagnostic/capture-20260911-121546.

Corrected the recorder to write a separate PID-named file with executable identity, and to retain one record per distinct exception address rather than spending the 64-record limit on one repeated site. Tests launch two processes concurrently and raise 80 handled exceptions per process. With recording on, each process writes its own complete log with one exception record; with recording off, neither writes a log. Both process handlers receive all 80 exceptions. All checks passed.

## Native experiment retired from the app

The final process-specific trace recorded backend initialization and a first-chance EndfieldBase.dll exception for Endfield.exe; PlatformProcess.exe had a separate Qt exception. Neither is proof of the fatal operation. The user confirmed the same menu warning and approved returning to the previously working ReShade workflow, with presets controlled through ReShade itself. The diagnostic was restored and source retained for investigation. Version 0.4.4 removes native installation and live NR controls from the desktop page and packages the ReShade workflow instead.

## Source location

The diagnostic backend sources referenced above (StartupTrace.h, the probes, and `tools/native_diagnostic.py`) are kept on the `experiments/native-nr` branch. Version 0.4.4 and later ship only the ReShade workflow.
