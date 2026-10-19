# Release 1.1.11 / Installer 1.0.16

Controller 0.1.82 tightens recognized YouTube subject rows while retaining personalized feed ordering, adaptive Refresh, card/watch state and continuation. Fresh Fire, Mac and Apple TV category/source/preservation/startup checks passed. Installer 1.0.16 and playback defaults are unchanged. See [validation](RELEASE_1_1_11_VALIDATION.md) for counts, hashes, scope and limits. Prior release assets and private recovery remain retained.

## Prior release record

# Release 1.1.10 / Installer 1.0.16

Controller 0.1.81 is verified on Fire Stick, Mac and Apple TV, including category continuation/relevance,45-second capped previews/fade, automatic fullscreen quality and source/settings/authorization/history preservation. Both portable editions use explicit clean YouTube defaults and Standard-update preservation of 18 YouTube playback choices. See [release validation](RELEASE_1_1_10_VALIDATION.md) for exact hashes, scope, native evidence and acceptance limits. Existing release assets and device recovery copies remain retained.

## Prior release record

The following record is retained unchanged for recovery and provenance; the release above supersedes its current-version labels.

# BlackLanturn distribution — 1.1.8

Kodi 21.3 Omega remains the target. BlackLanturn Repository and the OpenWizard-based BlackLanturn Installer retain their existing identities.

## Hosting and editions

GitHub Pages hosts repository metadata, Installer 1.0.13, setup guidance and the new catalog at `hosted-files/builds-v2.txt`. GitHub Release `v1.1.7` hosts exactly two current clean payload assets:

- General: Fire TV/Android, derived from the existing Fire Stick edition, with its tested YouTube fix and lower-memory defaults.
- Apple TV & Mac: Mac baseline shared skin/controller, with platform-native components retained. Apple TV quality was not reduced.

The old `hosted-files/builds.txt` remains upgrade metadata for older installers. Its old edition names and versions are retained, but payload links are retired. Update the installer to 1.0.13 before using the current packages. Never put the new payload URLs in the legacy catalog: older installers lack native-component preservation.

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


## Release 1.1.6 — Apple TV follow-up

Controller 0.1.74 fixes Help UTF-8 decoding, updates preview-language descriptions from saved preferences, and checks public YouTube titles against selected-title aliases before approving previews. Clean builds default to Kodi-interface audio language and forced-only subtitles. The requested Apple TV preference correction separately enables incoming Helper watched/progress metadata and persists the two language choices, preserving all other persisted userdata settings. Installer remains 1.0.12 and the managed Helper manifest is unchanged. All three devices passed the same native acceptance and restart/source/preservation audits, Fire Stick first. Focused Apple Help, language-choice persistence/labels, real wrong-series rejection, 20 watched identities and one resume-point comparison passed. Source checks: 523 controller, 122 installer/release and 10 maintained native-probe tests. Both reproducible packages passed exact-source and clean-default checks. See RELEASE_1_1_6_VALIDATION.md for evidence, acceptance limits and recovery.


## Release 1.1.7 — durable playback/Trakt install policy

Installer1.0.13 and schema3 packages explicitly validate all ten playback/Trakt defaults, preserve stored choices during standard updates, restore selected accounts on account-only clean, and retain the original pending snapshot across retries. Kodi default=true flags do not erase deliberate saved choices. Native tvOS XML uses authoritative VFS storage with readback instead of ordinary-file existence checks; cleanup includes native XML visible in existing userdata directories and installed-addon settings.xml after cache-directory eviction. Wholly orphaned native XML in evicted directories remains an acceptance limit. Controller0.1.74 and the reviewed Helper source/protection are unchanged. Native disposable Mac standard/KeepGUI/account-only-clean installer workflows passed, preserving80native files and selected accounts. Native Apple owned storage/capture/cleanup probes passed without a real-profile wipe. Source checks:189installer,523controller,10native-probe. See RELEASE_1_1_7_VALIDATION.md for live-device caveats, package hashes, evidence and recovery.


## Apple TV diagnostic storage correction — October 17, 2026

A slashless directory listing in an earlier diagnostic reproduced a Kodi 21.3 tvOS cache bug: virtual XML exists but reads as empty until its parent is listed with the trailing slash. This can cause addon settings to load as defaults before a later save. Maintained diagnostics now normalize directory URLs and validate XML without resetting unreadable files; explicit checks execute under optimized Kodi Python. Native owned-only regression passed, all 21 persisted Apple TV userdata entries remained unchanged after restart, and the same Trakt account returned HTTP 200. The build payloads and runtime addons remain unchanged. The underlying Kodi bug and unrelated callers remain outside this diagnostic fix. See TVOS-SETTINGS-CACHE-INCIDENT.md for the reproduced mechanism, evidence and limits.


## Release 1.1.8 — signed-in YouTube browser

Controller 0.1.75 adds account-aware YouTube Home, Search, Subscriptions, Library and Channels in the existing skin, automatic sidebar visibility, exact-video history-safe previews, an independent preview toggle, real adaptive account-interest rows, 16:9 thumbnail fallback and independent card focus. Exact YouTube.com browser Home is not exposed by the existing login. Native Mac acceptance passed on the exact source; playback/settings/authorization grants were preserved. Both clean editions package the tested source through Installer 1.0.14. The existing schema-3 playback/Trakt policy and managed Helper remain unchanged. Fire Stick/Apple TV personal devices were not updated or newly feature-certified. See RELEASE_1_1_8_VALIDATION.md and hosted-files/setup-1.1.8.txt for evidence, limits and recovery.


## Unpublished controller 0.1.76 — Fire Stick YouTube stall

The Fire Stick cancellation stall was reproduced and repaired in the maintained controller source. Exact source76 passed three preview cancellation stages, restored normal hardware playback, browsing/search/YouTube checks and ordinary restart, with 13 protected files and YouTube local history preserved. All 569 controller tests passed; independent review confirmed the cancellation/decoder restoration race correction. Apple TV was not accessed. This is a Fire-tested candidate only: published 1.1.8/controller 75/Installer 14 remain unchanged, and future promotion must use manifest76 after appropriate device acceptance. See YOUTUBE-STALL-FIRE-0_1_76.md and controller-source/youtube-stall-native-verification.json.


## Release1.1.9 — durable YouTube preview stall repair

Both reproducible editions and Installer1.0.15 now select exact controller0.1.76. The release gate requires matching Fire and fresh Mac native acceptance, decoder restoration, history/settings preservation and ordinary restart evidence. Both payloads change exactly seven approved paths from1.1.8; playback/Trakt/defaults and installer account/preservation logic remain byte-identical. Tests:569 controller,193 installer/release,16 native-probe. Mac27 protected files and the prior Fire13-file audit preserve settings/grants. Apple TV was not accessed or updated. See RELEASE_1_1_9_VALIDATION.md for evidence, historical visual provenance, distribution checks and limits.


## Release1.1.13 - three-device progress acceptance

Installer1.0.18 and full managed Umbrella6.7.92/event-progress-3 repair immediate seek/Stop, native duration refinement and selected-only zero-resume clearing. All four cases passed on Fire, Mac and Apple TV with source/settings/accounts/watched/unrelated-progress preservation. Apple also completed the real Installer Standard recovery into the current provider app; native imaging operations now pass, and language/subtitle values survive normal Quit/relaunch. Controller0.1.83/Helper source remain unchanged. Both managed addons have durable full-tree update protection and ZIP destination guards. Release v1.1.13 is published with three exact tested assets; candidate CI39192778558 passes and both anonymous build downloads match. Main/Pages activation is a separate distribution checkpoint. See RELEASE_1_1_13_VALIDATION.md for current evidence, rejected test attempts, native-provider limits and recovery scope.
