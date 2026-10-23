# Release 1.1.17 validation

The user authorized publishing the tested first-page discovery changes in both existing editions and the installer, while leaving Fire Stick and Apple TV untouched. Source starts at public 1.1.16 commit c9000d7. Only the tested discovery delta is included; earlier unpublished genre Options, similar-source playback and context-menu changes remain outside this release.

## Packaged behavior

Controller 0.1.86 adds bounded local ordering of explicit public Movies/Shows row pools. It does not request extra provider pages for uniqueness. All eligible relevant overlap remains available, and current provider objects retain artwork, watched and resume fields. Frozen order is scoped to configuration/account identity, row and provider page. Fresh-page intent starts at the ranked head; Back, vertical return and status refresh retain the selected title.

Both editions include the reviewed 19-row Movies / 16-row Shows defaults and all genre/category pages. Recently released, new-series and age-based discovery windows use Helper-supported t-N/t+0 dates; historical classics retain fixed historical boundaries. Existing anime eligibility filling and normal continuation remain unchanged. Personal recommendation/Home/YouTube/search/episode browsing are exempt from discovery reordering.

Installer 1.0.22 stores the reviewed public recipe catalogue in maintained source. During Standard restoration, only exact recognized legacy default row groups/pages are upgraded. Per-page metadata and disabled-page choices remain; customized groups, saved items, unknown preferences and non-discovery settings stay intact. Already-current or unknown configuration retains exact original raw JSON. Pending restoration is deterministic and does not resnapshot partially extracted defaults. Rollback to an older build does not apply the new migration. Clean installs receive the same catalogue. Build marker requires Installer1.0.22, and the prior installer refuses before cleanup. New preflight accepts only the approved full playback/Trakt/YouTube/Umbrella/network/autoplay policy combination and verifies the bundled discovery defaults before cleanup.

## Evidence and boundaries

The previous Mac comparison had 34 baseline and 71 candidate native browse captures. Median settled time across15 matched genre visits was0.6841→0.5965s; representative first-six-row repeat rates fell from21–31% to0–3%. These are limited shared-upstream-cache/hotel-network observations, not cold-download guarantees or proof of a universal speedup.

The exact release controller was run in an isolated Mac profile for16 native captures and Next/Back, vertical focus, watched-refresh and restored-provider-zero versus fresh-start checks. This smoke run was repeated after rolling-date correction. Test adaptation changes only profile/entry glue; product class bodies and all remaining controller files match the release manifest. Public sanitized receipt hashes bind the exact source and recipe catalogue. Full raw captures and accounts remain private. No video playback or remote watch/progress writes were required. Fire Stick and Apple TV were not accessed.

After the test the Mac's normal launcher and current installed setup were restored. Preservation passed for301 protected files,280 core preferences, four healthy unchanged history databases, favorites and315 installed controller files. Only normal mouse/keyboard last-active timestamps changed.

An independent read-only scoped review found two Important issues: unknown/weaker preferences policy could bypass compatibility checks, and rolling dates were frozen. Both were reproduced by failing regressions and fixed; corrected rolling recipes passed the native smoke. No other findings were reported; there was no second independent review after the fixes. The reviewer did not independently validate live preservation, native screenshots or public publication; parent-run checks account for those scopes. No other-device native acceptance is claimed.

## Reproducible release and preservation

Builder starts from the same hash-pinned sanitized1.1.2 baselines, never a personal profile. Relative to exact public1.1.16 archives, both editions differ in exactly11 approved paths: controller metadata/live renderer/new pure ordering module; installer metadata/preference restoration/preflight/new migration/new public catalogue; clean row defaults; release marker; README. Every other packaged file is identical, including platform-specific workarounds, Helper/Umbrella/network implementations, playback/default settings, skin and branding. Managed addon update protection remains unchanged.

Historical manifest85 and YouTube end-screen/native playback receipts are retained as historical acceptance. New manifest86 binds only the current discovery delta; source and recipe drift fail the release gate. No old receipt is presented as a fresh device test. The new installer is wrapped in a deterministic Kodi-correct ZIP; both editions embed that exact installer tree.

Standard preserves supported playback/Trakt/YouTube choices and selected Trakt/debrid/login authorizations. Users must keep the desired GUI/source/favorite/optional file Save Data switches selected. Account-only reset intentionally resets preferences and is not the requested update mode. Customized discovery groups are deliberately preserved rather than silently replaced; they can keep their existing recipes.

Publication sequence: freeze and verify source/assets, pass CI, publish immutable release assets, anonymously verify full hashes/lengths/CRC, then activate installer metadata and both catalog entries. Existing releases remain available. Public hashes, CI identifiers and final Pages activation are appended after verification. No personal device update is part of publication.
