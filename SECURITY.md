# Security

## Reporting a vulnerability

Please report it privately through GitHub rather than in a public issue: on this repository's
**Security** tab, choose **Report a vulnerability** (private vulnerability reporting). The report is
visible only to the maintainer until a fix is published.

Include the Fate Engine version, what you found, and how to reproduce it. Redact account
identifiers and personal paths from any logs or diagnostics you attach.

## Supported versions

Only the latest release on the
[Releases page](https://github.com/VagueDustin/arknights-endfield-fps-unlocker-enhanced/releases)
receives fixes.

## Scope

In scope: the native loader and runtime in `src/modern`, the manager and desktop app in `tools`,
and the installer, including how they back up, verify and restore game files.

Out of scope: the game itself, and vulnerabilities in third-party components (ReShade, MinHook,
NVIDIA components). Report those to their maintainers.
