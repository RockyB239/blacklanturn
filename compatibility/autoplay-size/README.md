# Mac hotel autoplay and polish trial

Mac-only local changes, based on published Build 1.1.14 / Installer 1.0.19 plus the earlier flat Options trial. No publication, installer edits, Fire Stick or Apple TV access.

## Behavior

With TV autoplay enabled, a successful manual episode source choice supplies a runtime-only show/season size ceiling for later episodes. Follow only the manually chosen debrid service, with no hardcoded TorBox preference. Normal autoplay without a manual choice keeps its existing configured source ranking. Keep an available release/pack match ahead of other similar-or-smaller candidates. Exclude unknown, nonpositive, nonfinite, uncached and folder results; try at most three candidates then show the existing picker. Explicit source selection overrides this policy. Stop/end-of-queue clears it; six-hour expiry is a backstop.

Both foreground selection and background preResolve consume the same policy. Prepared URLs carry the policy stamp and are rechecked before publication and consumption, rejecting a resolution completed after a smaller manual choice. Resolver fallback cannot increase the selected ceiling or widen its permitted service. Existing permanent preferred-pack behavior remains an additional constraint. No new per-source network searches are introduced. Pack sizes retain the provider's existing per-episode estimates.

Controller polish: selected show folders open first; episodes and films retain Play/Resume, player choice and flat account actions. Only background retry preserves the original focus; explicit folder Open enters the loaded child row. Local-save confirmation distinguishes this-device storage from the Trakt watchlist. Existing rows/art/watched/resume remain visible through controlled network failure and recovery.

## Verification

665 controller tests, 21 policy/dispatch/race/Stop tests and 87 current progress regressions passed. Independent review found the prepared-URL race, unknown-size resolver-fallback guard loss and overbroad focus preservation; failing regressions were added and fixed.

Native Mac matching selected the identical cached TorBox 720p release (estimated 0.1233 GB per episode), with approximately 0.0103 ms mean matching overhead. Same-file starts, alternating baseline/revised, were 7.409 / 3.385 / 2.641 / 2.221 seconds. The first run was cold; this is no proof of a speed increase. Source/URL identity was held constant to isolate playback from provider variation.

Real next-episode scrape returned 38 sources in 8.102 seconds. PreResolve selected the same TorBox pack under the same ceiling, prepared it in 3.227 seconds, and play() consumed the exact prepared URL with a 2.233 second handoff. The final player boundary used native untracked playback to avoid changing Trakt progress. This does not certify every natural end-of-episode dialog/timing path.

Native selected-item menus, retained rows, failed-page retry, stable focus and explicit folder Open passed. Existing settings, authorizations, rows/API JSON and all four saved history databases were preserved. The user completed TorBox device authorization; its two saved account fields are the only authorized settings changes. Original controller entrypoint is restored, no permanent diagnostic hook remains, and Mac is at Home with no active player.

YouTube first pass played inline 720p and automatic fullscreen 1080p with history disabled; a later preview demonstrated its normal fade. A repeat fullscreen attempt failed its player-context assertion and logs showed stream timeouts. Sustained fullscreen/4K acceptance remains for a stable network; this trial changes no YouTube quality or VPN settings.

## Known test/release limits

The 470-test release suite has 468 passes and the same two intentionally unchanged published-controller hash guard failures as the earlier Mac trial: test_repaired_search_release.RepairedRelease.test_controller_has_reviewed_repair_and_preview_safety and test_umbrella_build_contract.UmbrellaBuildContract.test_both_actual_builds_keep_controller83_defaults_and_only_reviewed_provider_changes. Do not treat this local trial as package-ready or weaken those guards.

The legacy OriginalProgressContract.test_seek_to_zero_then_stop_does_not_restore_prior_position fails for both apple/fire subtests when redirected to either the frozen current player or this candidate; that older fixture predates current zero-reset semantics. The 87 current zero/duration tests pass against the exact trial player.

Before later rollout: update version and managed source manifests, preserve platform workarounds, stage installers/builds, rerun release locks and perform clean-profile plus preserving-upgrade and device checks. Mac trial hashes and native evidence are in trial-manifest.json and mac-verification.json.

## Recovery

Fresh private recovery and host test scripts are retained in ../hotel-autoplay-mac-2026-10-19 (relative to this trial's top-level work directory); the original full settings/auth archive is private/settings-before.zip. To roll back code, quit Mac Kodi normally, restore private/live_review.before.py to addons/script.blacklanturn.preview/live_review.py and private/umbrella-{sources.py,source_preferences.py,player.py} to their original Umbrella module paths, then relaunch. Do not restore the old whole settings archive over the newly authorized TorBox connection. Stop to inspect if any installed hash differs from the saved trial manifest.

## Provider-following correction

User clarified that hotel TorBox use must not become a build-wide preference. The installed Mac policy now follows whichever debrid service the user manually selected. Native installed-module checks passed for TorBox, AllDebrid and Real-Debrid, including no cross-service fallback. Actual production play() tests confirm the configured provider/size ordering is untouched when no manual session exists. Matching the real 42-source snapshot averaged approximately 0.0096 ms. Fresh post-authorization settings backup and final comparison show zero settings/account/history changes. See provider-followup-verification.json; the original stream measurements remain historical evidence for the same TorBox case. This correction was not rolled out elsewhere.
