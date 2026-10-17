# BlackLanturn distribution — 1.1.2

Kodi 21.3 Omega remains the target. BlackLanturn Repository and the OpenWizard-based BlackLanturn Installer retain their existing identities.

## Hosting and editions

GitHub Pages hosts repository metadata, Installer 1.0.10, setup guidance and the new catalog at `hosted-files/builds-v2.txt`. GitHub Release `v1.1.2` hosts exactly two clean payload assets:

- General: Fire TV/Android, derived from the existing Fire Stick edition, with its tested YouTube fix and lower-memory defaults.
- Apple TV & Mac: Mac baseline shared skin/controller, with platform-native components retained. Apple TV quality was not reduced.

The old `hosted-files/builds.txt` remains upgrade metadata for older installers. Its old edition names and versions are retained, but payload links are retired. Update the installer to 1.0.10 before using the new packages. Never put the new payload URLs in the legacy catalog: older installers lack native-component preservation.

## Install safeguard

Validate ZIP integrity and platform before cleanup. Keep compatible device-native playback components and their preferences. Missing components use Kodi's official repository with the official-only repository policy. Cancellation, failed setup, an incompatible component or wrong platform stops before cleanup. After extraction, register installed addons in the device's existing database. Payloads contain no native binaries, device addon registry or personal credentials.

## Prior baseline validation

18 installer safeguard tests passed, plus independent source/catalog review. A disposable account-free Mac profile passed actual OpenWizard wipe/extraction, existing native-file preservation, addon registration, native cold start and movie browsing. Personal Mac and Apple TV passed targeted updates. Apple TV playback included 3840×2160 HEVC with English EAC3 5.1. Preview handoff, episode-to-play, cast/audio visibility, season posters, three Umbrella player choices and image-first Next Up were checked on Apple TV.

Full clean ZIP installation on the personal Apple TV or Fire Stick was not performed. Broader Android/Intel Mac hardware and credit-marker timing at a real episode ending remain untested. Fire Stick testing was not interrupted. Setup and recovery guidance: `hosted-files/setup-1.1.2.txt` and each payload's `userdata/BlackLanturn-README.txt`.

## Recovery

Previous clean editions are archived locally before cloud retirement. Private device recovery/preferences remain access-restricted and excluded from publication. Repository rollback is available through Git history; restore old payload links only when their corresponding verified downloads are available again.

Installer 1.0.9 originally corrected combined Apple TV & Mac card naming and removed the old Apple Silicon-only subtitle without changing the 1.0.8 native safeguard or 1.1.0 payloads. Release 1.1.1 now includes those tested installer labels in both payloads.

## Release 1.1.1

Both clean editions contain controller 0.1.41 (recoverable startup failure, bounded session row cache and Movies & Shows search) and Installer 1.0.9. Skin 0.1.38 and edition-specific quality/YouTube settings are unchanged. Both packages derive from verified clean 1.1.0 ZIPs, with all five userdata settings XMLs and rows.json byte-identical. No bedroom SDR filters or personal account data are included.

Startup/cache changes received targeted native testing on Mac, Apple TV and Fire Stick. Combined search received native Mac testing and regression tests; native combined-search testing on Apple TV/Fire Stick and new full clean-device installs are not claimed. Package verification checks CRC, all file hashes, dependencies and credential/native-binary exclusions. Publication does not update running devices. Previous 1.1.0 release assets remain available for recovery.

## Release 1.1.2 — managed Helper compatibility

Both clean editions now include Helper 6.17.9 with empty-cache-1 and Installer 1.0.10. Existing controller 0.1.41, skin 0.1.38, userdata settings, rows, quality defaults and edition-specific YouTube files are preserved. GitHub Release v1.1.2 hosts the two payloads. The current catalog requires Installer 1.0.10; the schema-2 marker makes 1.0.8/1.0.9 reject these payloads before cleanup. The legacy catalog retains retired links and updates only its installer header.

Helper is verified against a complete reviewed file manifest and protected with Kodi’s per-addon update rule before cleanup and after extraction. UpdateLocalAddons refreshes the in-memory rule. Future Helper versions must pass the native failure-cache suite and installer/package checks before a BlackLanturn build release distributes them. No background patching service or invented high version is used. Explicit manual Helper replacement or opting back into its automatic updates bypasses protection. See HELPER-UPDATE-POLICY.md for the maintained process.

New validation: 12 native packaged-Helper regression tests on Fire Stick; Kodi addon-info confirmed Auto-update off; real isolated Mac OpenWizard preflight/cleanup/extraction retained 80 native files and healthy registry with enabled protected Helper. Installer and packaging checks also passed. Fresh full personal Fire Stick/Apple TV installs are not claimed. Previous 1.1.1 assets remain for recovery; no personal settings enter these payloads.
