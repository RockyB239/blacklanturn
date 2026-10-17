# BlackLanturn distribution — 1.1.5

Kodi 21.3 Omega remains the target. BlackLanturn Repository and the OpenWizard-based BlackLanturn Installer retain their existing identities.

## Hosting and editions

GitHub Pages hosts repository metadata, Installer 1.0.12, setup guidance and the new catalog at `hosted-files/builds-v2.txt`. GitHub Release `v1.1.5` hosts exactly two current clean payload assets:

- General: Fire TV/Android, derived from the existing Fire Stick edition, with its tested YouTube fix and lower-memory defaults.
- Apple TV & Mac: Mac baseline shared skin/controller, with platform-native components retained. Apple TV quality was not reduced.

The old `hosted-files/builds.txt` remains upgrade metadata for older installers. Its old edition names and versions are retained, but payload links are retired. Update the installer to 1.0.12 before using the current packages. Never put the new payload URLs in the legacy catalog: older installers lack native-component preservation.

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


## Release 1.1.3

Both clean editions are assembled from verified 1.1.2 payloads plus exact validated controller 0.1.67 (301 files), its mandatory Helper search-empty-1 overlay, and Installer 1.0.11. The rejected 0.1.69/0.1.70 work is excluded. The explicitly accepted 64MB/fixed400/buffermode4/chunk131072 playback settings and High artwork defaults are now packaged. Hardware-specific SDR/decoder choices are not global defaults.

Installer authorization-only clean mode retains only selected known credentials for addons in the chosen build, clears optional preference/content preservation, resets native playback preferences while retaining the required platform-native binaries, and removes unused Python modules. The existing default preservation mode remains available. Native safeguards and the managed Helper rule remain. Pending account snapshots survive retries; legacy non-managed build preservation follows the prior path. Installer release details and clean-install instructions are in hosted-files/setup-1.1.3.txt.

Release v1.1.3 is published. Both anonymous payload downloads passed full hash/CRC/file-manifest verification, and the live Pages catalog, metadata and Installer 1.0.11 ZIP matched the release source. The maintained source and packaging checks passed CI. The final native OpenWizard isolation test and 12 packaged-Helper failure-cache checks passed.

A full personal Fire Stick installation through the published Installer 1.0.11 completed on 2026-10-17. The downloaded payload and all 36 packaged addon source manifests matched; the only additional physical addon was the required device-native inputstream.adaptive. After restarting Kodi, all selected authorization fields/files were unchanged, controller 0.1.67 and Helper source hashes matched, High artwork and the 64MB/400/4/131072 buffer defaults were active, and the existing addon database passed integrity_check with Helper automatic updates disabled. The separately approved Fire SDR/decoder compatibility choices were retained on that device only.

Acceptance limits: Home recommendations populated; an empty A24 collection search returned a successful empty directory; the TMDb weekly TV route populated. The configured Trakt Trending routes returned HTTP 429 during acceptance, and the failure-cache guard logged that the failed request would not be cached. This remains a provider limitation; clean installation does not prove that those rows or all watched markers currently load. A generated 720p H264 clip advanced normally after a slow initial HTTP stat/open. First clean startup and uncached A24 search did not establish a speed improvement. Full personal Apple TV clean installation and universal device/remote-stream reliability remain untested.


## Release 1.1.4 — missing functional defaults and preview retry race

Real use after the 1.1.3 clean install exposed acceptance gaps. Sparse sanitized preferences omitted Umbrella's enabled/assigned Cocoscrapers integration, YouTube's automatic stream selection and Helper's enabled Trakt watched indicators. Preserving accounts alone did not restore these required build defaults. Both reproducible payloads now set these noncredential defaults explicitly, and package verification rejects their absence. Edition quality limits, player choices, buffer defaults and account isolation remain unchanged.

Controller 0.1.71 fixes a separate evidenced race. The previous preview fallback launched a second candidate after 12 seconds while the first YouTube resolver remained active. The first resolver later opened its stream; Kodi logged MediaCodec InstanceGuard locked and failed codec creation. Slow resolution now cannot dispatch another candidate; fallback follows a terminal playback error. The rejected progressive-results work is excluded.

The new regression failed on the old timeout behavior and passed after correction; all 435 controller tests passed. The Fire Stick's actual Umbrella loader changed from zero to four providers. The Hill House preview remained embedded, advanced normally and stopped on navigation. The normal movie Play button opened Game Night in 3840x2160 HEVC with DTS-HD MA 5.1; it advanced and returned to browsing after stopping. This verifies targeted repair of the known clean-installed profile, not a second full 1.1.4 wipe, universal source reliability, all watched markers, or a browsing-speed improvement. Recovery and deferred experiments remain private and intact.

## Release 1.1.5 — repaired search and preloading

Controller 0.1.73 promotes the native-tested search/preloading overlay with lifecycle ownership and monotonic generation fixes; the 0.1.71 retry safety is retained. Installer 1.0.12 carries the exact 471-file Helper manifest with empty-cache-1/search-batch-1 and retains per-addon auto-update protection. Both clean editions package the maintained source and explicit playback, watch, artwork and buffer defaults. The rejected 0.1.70 progressive experiment remains excluded.

Source checks: 480 controller tests, 119 installer tests and fresh12-case native cache regression passed. Both1.1.5 packages passed exact-source and compatibility verification. Native acceptance and independent restart/source/preservation audits passed on Fire Stick, Mac and Apple TV. See RELEASE_1_1_5_VALIDATION.md for exact scope, crash diagnosis and limits.

The October17native crash reproduction identified a direct diagnostic artwork-label getter during row replacement. Maintained native probes now marshal coherent metadata snapshots through the GUI thread; controller0.1.73 also dispatches its label reads and rechecks row/preview ownership after waits. The native hold is lifted; see RELEASE_1_1_5_VALIDATION.md for evidence and limits.
