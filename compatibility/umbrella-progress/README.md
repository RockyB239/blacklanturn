# Umbrella progress source candidates

Current acceptance: event-progress-3 passed independent review, source regressions and four real native cases on Fire Stick, Mac and Apple TV using the exact packaged6.7.92 candidate. The source-bound native-verification.json is required by the release gate. Build1.1.13/Installer1.0.18 include the repaired source and full-tree update protection. Publication/hosted-byte evidence is recorded separately in docs/RELEASE_1_1_13_VALIDATION.md. Earlier unsuccessful revisions remain historical evidence below.

The defect is in Player timing ownership and callback ordering:

* `onPlayBackSeek(time, seekOffset)` discarded both arguments. `time` is the absolute destination in milliseconds; a relative offset cannot substitute for it.
* `keepAlive` waits five seconds before sampling, then samples at the existing one/two second cadence. A seek followed immediately by Stop can therefore leave the old cache intact.
* `_sendFinishedItemState` wrote the cached local bookmark and remote progress before calling `getWatchedPercent`; even a readable final native position arrived too late.
* `getWatchedPercent` rejected a valid zero position, and resumed playback used `getTime() or current_time`, restoring stale progress at zero.
* `onAVStarted` reset terminal flags before checking them and could overwrite a user seek that happened while its saved-resume delay/lookup was running.

The candidate captures finite absolute seek positions including zero; the existing sampler sites share a finite local timing snapshot. A pending seek protects that event destination while the native getter still returns the previous position. The pending state clears when native time reaches the destination (including paused target) or valid elapsed advancement near it. Wall-clock time is used only to recognize an acknowledged seek; it never creates progress. No poller, thread, timer, network request or idle work is added. The existing keepAlive cadence remains intact.

Terminal writes sample before sending when timing still exists and retain the callback cache after Kodi discards timing. Late AV initialization cannot reopen a closed item or reapply its saved offset over an explicit user seek. The existing `_playback_path`, populated from Kodi's resolved `getPlayingFile()`, prevents the old Player from sampling the next item's clock. It is not compared against the plugin metadata URL.

For frozen event-progress-1, all Bookmarks methods and all provider modules remain unchanged. Seconds-based provider start payloads share the same validated seconds/duration snapshot as their percentage. All existing provider authorization/source gates remain in place. The 6.7.92 file is patched in place; it is not replaced with 6.7.90 or an older addon tree. Unknown input hashes are rejected by the candidate builder. Integration must apply these overlays only for the exact reviewed original/patched file hashes and protect the applicable Umbrella update path without overwriting unknown newer addon code.

## Provenance

`upstream/6.7.90/player.py` is byte-identical to the player in the clean Apple-TV-Mac 1.1.12 package and the restored Apple profile. `upstream/6.7.92/player.py` is the preserved Fire player from its bounded software capture. `manifest.json` records the before and after SHA-256 for each variant. Source fixtures contain addon code only, without user settings, account data, media URLs or logs. `source-audit.json` lists changed functions; the version-specific `.patch` files show the complete narrow difference.

## Reproduce

From the release checkout root:

```sh
# Expected RED: 23 test methods, 52 failing version/edge-case subtests.
UMBRELLA_PROGRESS_UPSTREAM=1 python3 -B -m unittest discover -s tests -p test_umbrella_progress.py -v

# Deterministically reproduce both candidate sources and manifest.
python3 -B compatibility/umbrella-progress/build_candidates.py

# Expected GREEN: 23 test methods, both actual version classes, OK.
python3 -B -m unittest discover -s tests -p test_umbrella_progress.py -v
```

The harness compiles the full actual Player class and actual Bookmarks.set_scrobble function unchanged from each selected source. Only Kodi state, local persistence and HTTP/provider boundaries are substituted. Assertions inspect the percentage reaching the provider boundary and the position reaching local bookmark persistence. Tests cover immediate seek/Stop, cold no-AV seek/Stop, backward and zero seeks, finite timing, invalid duration, delayed native acknowledgement, paused time, normal saved resume, user seek during AV initialization, Stop-before-AV-ready, same-item identity, next-item isolation and duplicate Stop.

The initial source proof sent 0.4663557628 percent (28 seconds) after an absolute seek to 750 seconds; the required result is 12.4916722185 percent for a 6004-second fixture. These are deterministic source-contract results, not a native-device or remote-account acceptance claim. Native before/after tests must precede any build/Installer release.


## Explicit-zero revision: event-progress-2

Status: local source and real SQLite contracts verified; Fire native exact-zero and positive-progress acceptance passed on the reviewed 6.7.92 source. Mac cold-start testing exposed a duration gap; event-progress-2 therefore does not satisfy cross-platform acceptance. `zero-candidate/`, `manifest-zero.json`, and `build_zero_candidates.py` stay separate from the frozen event-progress-1 files so its native proof remains reproducible.

Native Fire evidence established that Trakt rejects a zero-percent pause with HTTP 422 and the message `Progress should be at least 1.0% to pause.` Positive progress already passed real callback/request/cloud tests. An exact-zero seek must therefore clear that item's existing resume record instead of submitting an invalid pause that leaves its old position visible.

The new revision retains the accepted absolute seek target independently of pending native acknowledgement. Only exact target zero, cached position zero and a valid positive duration permit the new terminal route. Inside the existing configured Trakt gate, it refreshes playback IDs and reuses `scrobbleReset` for this item's resume ID with `refresh=False, clear_local=True`. It never changes watched history, configured providers, accounts or settings. Nonzero requests and the other six providers keep their prior behavior; no zero-to-one-percent clamp is used. Nonzero positions below the API's one-percent pause minimum remain an external API limit outside this exact-zero revision.

`Bookmarks.reset` gains `clear_zero=False`; its existing targeted title/year delete runs for an explicitly permitted zero, without inserting another bookmark. Ordinary failed-start zero and invalid-duration cases retain their prior cleanup behavior. No new sync/reset request occurs without the accepted zero target, a known duration and the existing configured Trakt gate.

The additional real-source suite executes the actual `Bookmarks.reset` against temporary SQLite data, checks selection of only this title's resume, rejects absent/invalid authorization conditions, retains other providers' zero payloads, guards duplicate Stop and re-runs the complete prior 23 behavior contracts on both new version variants. The one old zero-pause assertion is updated to the intended resume-clear contract for this revision. `source-audit-zero.json` and the `zero-from-frozen-*.patch` files show the three changed functions.

```sh
# Reproduce both separate zero candidates and manifest.
python3 -B compatibility/umbrella-progress/build_zero_candidates.py

# GREEN: 32 test methods against both exact new source variants.
python3 -B -m unittest discover -s tests -p test_umbrella_zero_resume.py -v
```


### Fire native acceptance of event-progress-2

The real native cold-start callbacks reported 750,000 ms then 0 ms before AV tracking was ready. Stop began 1.506 seconds after the player appeared. The existing reset route deleted exactly the matched selected resume record with HTTP 204; the selected title was absent in both immediate and settled cloud reads. No invalid zero-percent pause was sent. A second cold 750-second Seek/Stop on the same reviewed code sent 12.4909399049 percent; both cloud reads held 12.4909 percent, a 0.0024-second difference from the actual 750-second destination. All watched history and unrelated resume entries remained unchanged in both cases.

After testing, diagnostics were removed and the final 2,625-file source inventory differed from the original in only the reviewed player.py (`83e68cc7f91c4814c00b668d7861e685691e08ad5a9e273b891a5315c07f8769`). Trakt, Helper and all other files were restored exactly. Settings/auth, sources, rows, favourites and addon registry rules were preserved; native XML serialization/order, total uptime and keyboard last_active bookkeeping are explicitly accounted for. The final state was Home, loading false, with no active player. No Kodi app/build installation, whole-addon replacement or profile wipe was performed during this reversible source code test.

The task retains the full attempts, request/callback traces, cloud comparisons, preservation proof and inverse recovery under `private/progress/fire/`, including `native-zero-verification.json`, `native-zero-preservation.json` and `quiet-final-zero-settled.json`. These native observations do not claim that a future packaged build or Installer transaction has been validated.


## Duration and position revision: event-progress-3

Current revision: independently reviewed and native-tested on all three devices; packaged in the held1.1.13 artifacts with Installer1.0.18. Frozen event-progress-1/2 and failed attempts remain intact. Distribution requires the separate release checks.

The Mac cold-start failure had this item's metadata duration available before resolve, but the instance still held duration zero when queued Seek/Stop callbacks arrived after native timing disappeared. The candidate seeds finite positive normalized metadata duration in seconds before resolve; the first valid native duration replaces that approximate fallback in either direction. No units are guessed.

A callback beyond approximate metadata retains its absolute target and marks duration unknown. A first native duration can also disprove a target previously within the metadata fallback. Such contradictions withhold duration-dependent local/provider writes until a consistent native duration and position are accepted. An impossible pending target is discarded only when an in-range native clock exists; still-valid pending targets retain their existing acknowledgment policy. Native-authoritative overlength callbacks remain rejected. No duration is inferred from a seek, and no percentage is clamped to manufacture a write. Ordinary failed-start cleanup without metadata retains its prior behavior.

The 55-method suite runs both actual source variants, including all prior 32 contracts, actual pre-resolve metadata normalization, unavailable clocks after teardown, both directions of native duration correction, every provider's terminal/start/reset boundary, and a real existing keepAlive iteration. Frozen inputs, reproducible candidates, hashes and complete deltas are in `build_duration_candidates.py`, `manifest-duration.json`, `duration-candidate/`, `duration-from-zero-*.patch` and `source-audit-duration.json`.

```sh
python3 -B compatibility/umbrella-progress/build_duration_candidates.py
python3 -B -m unittest discover -s tests -p test_umbrella_duration_fallback.py -v
```

Expected source-test result:55 tests, OK. Native acceptance is established separately by native-verification.json and the release validation record.
