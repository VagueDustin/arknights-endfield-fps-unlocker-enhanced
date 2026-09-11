# Upstream provenance audit

Audit date: September 11, 2026. Compared the local working tree with upstream baseline `0900219a4fcbac7cabbb95924dcb7fa80c579b02`. Counts include blank lines and comments and are not a measure of copyright ownership or a plagiarism analysis.

## Repository status

GitHub reports `VagueDustin/arknights-endfield-fps-unlocker-enhanced` as public, `isFork: false`, and ADMIN access for the authenticated owner. It is already an independent repository. Historical commits and attribution do not give the original author administrative control over this repository.

## Code retained and code built

Before cleanup, all 19 inherited files under `src`, `bin`, and `deps` were unchanged (comparing text with normalized line endings). These included 11 old source/resource files totaling 2,166 lines, five historical binaries/config files, and three vendored MinHook files. At the user's request, those 19 unused files have now been removed locally from the current tree after verifying their contents against the baseline. Git history preserves them.

None of those old source files is compiled by the current CMake build. The native production targets use `src/modern/runtime.cpp`, `graphics.cpp`, and `loader.cpp`, with the modern header and compiler export definition. MinHook is fetched separately at a pinned upstream commit.

| Current area | Files | Lines |
| --- | ---: | ---: |
| Modern native implementation | 5 | 743 |
| Python app and tools | 10 | 1,249 |
| Tests | 7 | 664 |
| Installer | 1 | 64 |
| Build workflow | 1 | 66 |

Counts were taken before adding this audit and contribution documentation. Assets, generated files, third-party dependencies, documentation, and CMake are excluded from the table.

The active implementation resides in newly added files, but it grew out of the original project and retains related techniques and API usage. This is not evidence of a clean-room rewrite or a basis for removing original notices. The existing MIT license requires retaining applicable copyright and permission notices.

## Maintenance model

VagueDustin owns the project and controls merges. Contributors can fork this independent repository and send PRs. CONTRIBUTING.md, a PR template, and CODEOWNERS are prepared locally. CODEOWNERS identifies the reviewer; enforcing required reviews would require a separate GitHub ruleset configuration.

The root MIT license now names VagueDustin Enterprises for this project's contributions. The original author's complete MIT notice is preserved in `licenses/EightySixK-MIT.txt`, explained in THIRD_PARTY_NOTICES.md, and included by the source and binary packaging steps. No history rewrite or repository deletion was performed. All changes remain local pending approval.
