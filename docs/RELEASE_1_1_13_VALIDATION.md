# Release1.1.13 validation

Native device acceptance and local package verification complete. Distribution publication, CI and anonymous hosted-byte checks are pending and must be recorded separately; this document does not itself assert publication.

## Repair and bounded runtime scope

Build1.1.13, Installer1.0.18 and unchanged controller0.1.83 package the complete official Umbrella6.7.92 tree with event-progress-3. The packaged player SHA256 is904b7eb226045610c213e5083a55d99b4462620b1089fb413a4e2e1b04f1b00c. Official upstream ZIP SHA256 is8dc3b19e70d0e02deb32d06579441288dbe1911ecaec2628d298590e1333853f; only its reviewed player source is changed.

Previously an absolute seek immediately followed by Stop could arrive before AV tracking initialized or after Kodi discarded the native clock. Umbrella ignored the absolute callback and wrote stale cached progress. The repair captures finite absolute milliseconds, seeds only a valid current-item metadata duration before resolution, and replaces that fallback with the first valid native duration in either direction. Contradictory duration/position snapshots withhold progress writes until a coherent native snapshot is available. Exact accepted zero clears only the selected resume record through the existing configured Trakt route; it does not send a rejected0%pause, clamp to1%, or delete watched history.

The existing wait/sampling cadence remains; no extra browsing requests, timer, background thread or continuous sampler is added. Targeted tests do not establish a new browsing benchmark or sustained4K/source/network reliability. Metadata fallback is approximate: its measured error is disclosed below.

## Native acceptance on all three devices

All tests execute the exact packaged6.7.92 candidate, real Kodi callbacks/clocks and real Trakt requests. The source-bound native-verification.json is required by tools/verify_release.py; older6.7.90 native tests cannot approve the6.7.92 packages. Diagnostic loaded-source digests, inverse source restoration, settings/authorization comparisons, actual watched/unrelated cloud comparisons and clean restart/quiet Home evidence are retained privately.

| Device | Cold player-to-Stop action | Cold cloud position error | Measured pause | Native pause drift | Selected-zero result |
|---|---:|---:|---:|---:|---|
| Fire Stick | 1.228s | 0.002s | 4.443s | 0.000s | 204 / two absent reads |
| Mac | 0.507s | 0.456s | 4.322s | 0.000s | 204 / two absent reads |
| Apple TV | 0.513s | 0.456s | 4.366s | 0.004s | 204 / two absent reads |

Cold Seek750,000ms/Stop occurs before AV tracking is ready. Both immediate and settled cloud reads match each tested destination within two seconds; observed errors are under one second. Saved-resume cases replace the metadata fallback with the actual native duration. Paused playback remains stable within0.1second. Zero cases match the deleted record to the previously observed selected title and verify absence twice. Watched history and unrelated progress stay unchanged. These are targeted correctness tests, not a timing precision or full movie-playback claim.

Apple attempt1 selected a scraping dialog prematurely; attempt2 requested an unsupported GUI property. Neither reached playback or passed acceptance. Attempt3 selected only an actual cached, non-folder result after the real source-results list initialized on the GUI thread. It preserved every protected XML/JSON byte during the four playback cases and restored all three diagnostic source files. Failed attempts remain private; no clock/callback/provider response was injected.

## Installer and update durability

Installer18 verifies the complete managed Helper and Umbrella trees before cleanup, protects both normal update paths, and rejects unknown/newer/foreign sources before destructive work. Shared ZIP validation rejects dot, repeated-separator, traversal, symlink, duplicate, casefold, Unicode normalization and implicit-directory aliases before hashing/extraction. Canonical legacy paths remain supported. Kept/whitelisted managed code must equal the reviewed target; otherwise installation stops with guidance to edit the whitelist. Registry protections are atomic and restored on failure.

The managed policy remains schema3, now playback-trakt-youtube-umbrella-1 with minimum Installer1.0.18. Existing pending account/controller/playback preservation is retained. Standard preserves stored choices, including deliberately saved upstream defaults; Account-only reset uses the tested build defaults and selected accounts. No live profile, native binary, private history or recovery archive is packaged.

An actual Apple TV Standard recovery used Kodi's normal ZIP UI to install Installer18, verified all163 Installer files, and executed the real Wizard workflow with its real confirmation/downloader/preflight/cleanup/extraction/preservation/registry steps. A private catalog override existed only in that invocation's memory. Native installed receipt: build1.1.13, extract100, errors0, authorizationsrestoredtrue. The4MB preference cap and fail-closed policies remain.

The new native registry passes quick_check and contains updateRule1 for both managed addons. All3,823 addon files from the clean Apple payload match installed bytes after diagnostics are removed. Stock cache-only metadata/version-check addons removed by the actual Standard install are not claimed preserved. No new native Installer18 Account-only-clean Apple wipe or new sustained4K validation is claimed; historical isolated Installer17 mode tests remain historical.

## Apple application repair and user-state recovery

The legacy provider refresh left PIL extensions signed for a different team and native import still failed. With explicit user approval for profile replacement, managed-app data deletion and recovery, the current KTB2 profile was installed and trusted. Separately approved Terms2026-09-08.1 and Privacy Summary were accepted. KodiTVBox2.1 installed Kodi21.3 through its own five-stage process; no app binary was sideloaded by this task.

The new package resolves the original imaging signature failure: four actual non-Tk native extensions import from the installed app. Pixel read/write, crop, resize, mirror, drawing, alpha composition and exact-pixel PNG encode/decode pass. Captured native signature code pages verify; all five PIL extensions and InputStream.Adaptive now match the main signing team. The broader diagnostic remains overallfalse because desktop _tkinter is absent and this provider package has no embedded.mobileprovision file. This is not an all-optional-module or universal-provider certification. No ImageTk/tkinter dependency was found in the reviewed Installer/managed compatibility paths. The portable build cannot repair another provider's signing; no native libraries or management profile enter either build.

A verified stopped backup covered4,618files/208,147,531bytes and29 healthy SQLite databases. Selective recovery into the new provider profile restores the present build addons' saved accounts/preferences, all three account/layout JSON files,45 Installer user preferences without overwriting its new receipt,28 default skin choices through Kodi's skin API, and58 supported playback values. One old DTS passthrough key is unavailable on the current platform and is not written. Optional addons outside the clean payload are not reinstalled. New registry/native components are retained; no old plist, migration marker, addon database, native library or stale Trakt cache is transplanted. Old YouTube history/bookmarks and Umbrella bookmarks/favourites held no user rows, so historical data replacement was unnecessary.

Runtime language changes initially passed immediate readback but had not been saved before controlled termination. Final acceptance uses a normal Kodi Quit, verifies process absence and the persisted profile, then verifies after relaunch that audio follows the interface language, subtitles are forced-only and Unknown sources is back tofalse. Account values match the original backup, except a consumed transient Helper invalidation flag; native empty skin strings normalize to omitted defaults. Protected settings/account files remain byte-identical during playback. The final normal source entrypoints are restored and Home is ready with no player.

The owned clean-artifact server is stopped; private test folders, source overrides and the temporary network source are removed. A clean public InstallerZIP in the tvOS Inbox could not be inspected/deleted by Kodi because the provider sandbox denies that location; it is not an executable diagnostic or private account archive. Full private recovery/evidence copies remain on the host.

## Package and publication checks

Both held payloads reproduce from hash-pinned public1.1.2 baselines plus maintained source. Their userdata bytes match the accepted clean1.1.12 defaults except the release marker and README. Four rating sources, automatic YouTube quality, existing preview policy/artwork/watch status, language/subtitle and buffer defaults remain; controller0.1.83 and managed Helper source are unchanged. Exact wrapped Installer18, full managed manifests, source syntax, ZIP CRC, path guards, clean-default checks and three-device native gate pass locally. Previous published assets and recovery copies are retained. Final source/known-private-value egress, metadata/XML/MD5, CI and anonymous release/Pages byte verification must pass before promotion is declared complete.

## Final local regression checkpoint

All 450 installer/release tests, 659 controller regression tests and 16 native-probe tests pass. The missing-native-receipt regression explicitly mocks an absent receipt independently of checkout state; the production acceptance gate is unchanged. Independent review reports no remaining Important findings. The exact publication inputs and all three ZIP artifacts pass the known-private-value scan against 19 protected archives and seven persisted preference snapshots (38 private values checked; no findings).
