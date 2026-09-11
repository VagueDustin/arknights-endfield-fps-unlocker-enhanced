# Contributing

Pull requests are welcome at https://github.com/VagueDustin/arknights-endfield-fps-unlocker-enhanced. This is an independently maintained repository owned by VagueDustin. Contributors can fork this repository, make a branch, and submit a PR; repository write access is not needed. VagueDustin reviews and decides what merges.

Use focused changes and describe the user-visible problem, resulting behavior, and validation. For runtime changes, report the game build, rendering API, and exact component versions tested. Redact account identifiers and personal paths from logs.

The current implementation is in `src/modern`, with the desktop and manager in `tools`. Unused upstream source and binaries were removed from the current tree and remain accessible in Git history. Do not reintroduce historical binaries.

Run `python -m unittest discover -s tests -v`. Native changes also require the x64 MSVC CMake build and `ctest --test-dir build -C Release --output-on-failure`; see DEVELOPMENT.md and the Windows workflow. State clearly when a change has only automated coverage and has not been validated in gameplay.

Preserve backup ownership, integrity checks, restoration, and runtime compatibility checks. Do not add game binaries, private data, or third-party runtime downloads to the repository. Experimental rendering integrations must document provenance, license/distribution requirements, and which settings can actually change live.

Contributions are made under this repository's MIT license. Keep applicable third-party notices and attribution. A PR does not grant its author repository administration or merge access.
