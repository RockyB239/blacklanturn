# Mac hotel autoplay and polish trial

Mac-only local changes, based on published Build 1.1.14 / Installer 1.0.19 plus the earlier flat Options trial. No publication, installer edits, Fire Stick or Apple TV access.

## Behavior

With TV autoplay enabled, a successful manual episode source choice supplies a runtime-only size ceiling for later episodes, including later seasons of the same show. Follow only the manually chosen debrid service, with no hardcoded TorBox preference. Normal autoplay without a manual choice keeps its existing configured source ranking. Keep an available release/pack match ahead of other similar-or-smaller candidates. Exclude unknown, nonpositive, nonfinite, uncached and folder results; try at most three candidates then show the existing picker with an explanation. Explicit source selection overrides this policy. Stop/end-of-queue clears it; six-hour expiry is a backstop.

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

## Current Mac polish validation

Local additions show “Following your selection” with the chosen service and reported size cap on matching episode selections, plus a flat “Return to normal autoplay” action. Reset invalidates the runtime choice and prepared URL without editing global preferences or permanent pack choices. Window reads are cached for two seconds during scrolling; Options forces a fresh read. Native repeated-read overhead fell from about 31 ms to 0.4 ms averaged across 100 reads. A post-wait stamp check closes a reset race in prepared-URL consumption. Malformed session scopes are ignored. Cross-season scope, missing-match notification, reset, cache and artwork/watch-state preservation have regression coverage.

Initial polish checks: 671 controller tests, 24 distinct policy/dispatch/race/Stop tests and 87 progress contracts passed; final callback coverage is recorded below. Native indicator/reset checks pass. The corrected YouTube test completed inline 720p with its 45-second fade, then 25 seconds of advancing automatic fullscreen 1080p VP9. Its earlier fullscreen failure was an invalid assertion against a property YouTube consumes on AV start; the test now observes the playback-init notification. No YouTube product patch was required. This observation does not establish 4K or long-session network stability.

Continuous natural-episode and real Trakt Stop/resume acceptance is still in progress. A temporary test-cancellation command deadlocked Mac Kodi's StopScript/GIL path; its thread sample is retained privately. The process was restarted and all four saved history databases passed integrity checks. This diagnostic command is not part of the controller, Umbrella patches, installer or build. Do not reuse synchronous StopScript cancellation for these native RPC observers.

## Final local Mac callback acceptance

The actual natural playback run exposed two lifecycle faults that native untracked playback had not covered. Kodi broadcasts an outgoing EOF to a next Player before acquisition; that prematurely set its terminal flag and prevented AVStarted/Trakt tracking. Separately, native playlist position may advance before the outgoing terminal callback, particularly after the existing still-watching pause. Cleanup based only on that live cursor could discard the next episode's source session and prepared URL.

The candidate now ignores pre-acquisition EOF, finalizes delayed outgoing cached progress without cleaning the active item's source session/queue/subtitles, and remembers the playlist position acquired with playback. That position distinguishes a queued handoff from the normal explicit Stop path. Failed-start, early seek, explicit-zero and same-position Stop behavior retain their current contracts. Twelve lifecycle regressions are included in 36 source/lifecycle checks; all 671 controller and 87 current progress tests also pass. Independent review caught and corrected an overbroad intermediate Stop guard before adoption.

Final installed-candidate evidence: a bounded seek approached an already naturally exercised EOF boundary; the unchanged three-episode still-watching/pause preference fired and was resumed. Native trace showed the outgoing item acquired at position 0 while EOF arrived with position 1/size 2. The next item retained the source session and played the exact prepared URL. Explicit Stop saved about 70.1 seconds to Trakt; actual resume started at about 71.1 seconds, then final Stop cleared the override. The temporary viewing counter was a runtime-only test setup, cleared at Stop; no saved setting was edited. This is not an uninterrupted three-episode acceptance claim for the final revision.

Final native indicator/reset/menu order and artwork/watch metadata checks pass. The cached label read averaged about 0.14 ms over 100 reads. All 280 core settings, 16 add-on settings files, saved rows/API JSON and four healthy history databases matched the fresh backup. YouTube renewed only its normal access token/expiry with identical accounts and refresh authorization. Original entrypoints are restored and Kodi restarted normally with no active player or diagnostic observer. Final sanitized evidence is in polish-verification.json. All three patch artifacts were applied to their frozen baselines and compared byte for byte with the candidates.

Fire Stick work was deferred at the user's direction after both control ports remained unreachable on hotel Wi-Fi, including an authorized brief VPN-disconnected test. No Fire Stick code was changed; hotel client isolation remains a possibility, not a confirmed diagnosis. Apple TV and public builds/installer/catalog remain unchanged. Retain this local trial and recovery evidence for the later authorized rollout.
