# Release 1.1.15 validation

Status: staged candidate; publication and anonymous public readback pending.

Both editions include the exact Options/retained-row retry implementation and three Umbrella modules tested in local commit `0b674a3`. Controller 0.1.84 differs from that tested controller only in addon version metadata. Installer 1.0.20 and the new `same-show-source-1` marker prevent an older installer from reaching cleanup with an unsupported payload.

## Playback acceptance

The unchanged final implementation completed four consecutive natural episodes on Mac across one season boundary, with no seeking and no simulated viewing count. The existing still-watching pause was confirmed without changing its saved preferences. All four subsequent prepared source paths matched their actual playback paths, retaining the manually selected service and size ceiling. Four completed episodes reached Trakt as watched, while the fifth stayed unwatched. Its partial Stop at 70.069 seconds resumed from Trakt at 69.765 seconds. Source-bound, sanitized evidence is `compatibility/autoplay-size/natural-verification.json`.

All 280 core settings, 16 add-on settings files, four healthy saved-history databases, existing account JSON/rows/API keys and untargeted show progress passed preservation checks. Installed entrypoints and implementation hashes were unchanged. Playback, diagnostic queue and temporary source state were cleared. Raw receipts and recovery snapshots stay private and are not packaged.

New playback acceptance is **Mac only**. Fire Stick and Apple TV were not contacted or updated during this release. Existing three-device progress/YouTube/network receipts remain historical evidence for retained source and are not relabeled as current-device acceptance. New device validation is deferred until the user returns home.

## Packaging and preservation

The builder still starts from hash-pinned clean 1.1.2 payloads, never a personal profile. Against anonymously verified public 1.1.14, exactly 14 paths change per edition: five installer files, four controller files, three Umbrella modules, the release marker and README. Every other file, all remaining userdata and each edition-specific workaround remain byte-identical. No private authorizations, history, databases or native binaries are introduced.

Installer preflight accepts only complete known Umbrella source inventories using canonical full-tree digests, including the exact former release trees and current trial. Mixed independently reviewed files are not accepted as an unreviewed combination. Unknown/future/link/extra-file and archive alias guards, transactional update protection and managed whitelist checks remain. Existing Standard preservation retains supported playback choices and selected authorizations, including TorBox and Trakt. Account-only remains an explicit reset mode. Installer19 refuses the new policy before native setup or cleanup.

Controller, source/lifecycle, current progress, native-probe, full installer contracts, deterministic rebuild and source-bound artifact checks are run before promotion. Final counts and CI/public readback are recorded below when complete. Existing OpenWizard fixture ResourceWarnings and upstream escape-sequence DeprecationWarnings do not indicate failed assertions; they are not new runtime behavior.

## Frozen artifacts

- `plugin.program.blacklanturninstaller-1.0.20.zip`: SHA256 `f2ab32e87074c1dd333bc6ec3ba16b93a7286f523fd45c0813b6d646fe70e3da`, 3748828 bytes.
- `BlackLanturn-General-Kodi21-1.1.15.zip`: SHA256 `8306ab3e462af0a4cbb8d64ecfe8ccdb2e9f059d8ddf945933c4966122bc680e`, 91049358 bytes.
- `BlackLanturn-Apple-TV-Mac-Kodi21-1.1.15.zip`: SHA256 `b01d6da9bdf48e05f4ae93d4dea584fafc588a717b48e0d20ae2ff7eee74066e`, 91864902 bytes.

## Final local verification

- 572 installer/release tests passed, including 87 current-player duration/zero/Stop contracts and deterministic rebuilds of both editions.
- 671 controller checks, 36 source-choice/lifecycle checks and 16 native-probe contracts passed.
- Full artifact verifier and exact 14-path delta checks passed for both editions; remaining userdata/platform source is exact.
- Private-value egress check found no matches for 16 private credential values across changed source and all three archives; one already-public baseline default was excluded.
- Independent whole-branch review found no Critical/Important or material minor findings and independently passed 30 focused integration tests plus package/metadata/source checks.
- git diff --check passed. No personal device was changed during release packaging.
