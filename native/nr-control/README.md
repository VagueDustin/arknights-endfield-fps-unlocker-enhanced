# Fate Engine native NR control

This component is licensed GPL-3.0-only and is compiled into the separate OptiScaler backend. The Python desktop client communicates through a documented shared-memory layout and contains no copied renderer implementation.

Pinned backend: `wilsjo2/OptiScaler-DLSSNR-PreSR-Multipass` commit `e237f895623742b761f9e5f00067cb3dc62619f4`.

`tools/build_native_nr.py` copies the two headers and inserts calls at the Vulkan NR evaluation boundary. `Tick` runs before the enable check, so a disabled pass can be enabled from the app. `Rendered` runs only after successful NR evaluation and composition dispatch. This acknowledges recorded Vulkan work, not GPU completion or visual correctness.

The endpoint is `Local\FateEngine.NR.<pid>` using the process token's default Windows security descriptor. It refuses an existing mapping. The app opens an existing endpoint and never creates one. A separate named writer mutex serializes app instances. The 128-byte version-1 layout uses aligned sequence fields for coherent request/status reads. Requests contain no paths, pointers, commands, or arbitrary memory addresses. Both sides validate every setting. NaN, infinity, unknown enum values, and out-of-range strengths are rejected.

Insert toggles NR only while the owning game's window is foreground. The upstream overlay shortcut is disabled in the private package to avoid duplicate handling. Shared memory is transient; settings are not saved to the game INI by the live controls.

Build the isolated transport probe with `native\nr-control\build-probe.cmd`, then run `python tools/test_native_transport.py`. This verifies transport and rejection behavior, not neural rendering.

The private installer stages the user's NVIDIA runtime for local validation. It is not a public redistribution build. Native rendering and hotkey behavior in Endfield still require a game test.

Startup diagnostics are opt-in through [FateDiagnostics] StartupTrace=1 in the diagnostic INI only. StartupTrace.h observes selected first-chance exceptions and always returns EXCEPTION_CONTINUE_SEARCH. Records include the module path and offset, and are capped at 64. A recorded exception can be handled normally and is not itself proof of a crash. An explicit process termination or fail-fast may produce no exception record. No exception is suppressed and no protection checks are changed.

Run native\nr-control\build-startup-trace-probe.cmd from the repository root, then python tools/test_startup_trace.py. The probe verifies enabled/disabled behavior and that the application's own exception handler still executes. These checks do not establish game compatibility.
