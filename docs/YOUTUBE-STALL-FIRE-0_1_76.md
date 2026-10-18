# Controller 0.1.76 — Fire Stick YouTube stall repair

Status: promoted into release1.1.9 / Installer1.0.15 with fresh shared-controller Mac acceptance. Original Fire proof remains unchanged. Apple TV was not accessed. See RELEASE_1_1_9_VALIDATION.md for release validation and distribution scope.

## Confirmed failure

An exact controller 0.1.75 replay stalled while a YouTube decorative preview opened and navigation stopped it. Native Kodi logs showed VideoPlayer opening, then CloseFile waiting for decoder threads during Android texture MediaCodec initialization. The controller worker was blocked in the synchronous GUI-label drain after Stop, and its monitor waited on the preview dispatch lock.

Kodi 21.3 Android texture MediaCodec initialization sends a synchronous UI-thread callback from its decoder worker. Processing Stop on that UI thread during startup can instead wait for the worker. The native trace and log sequence match this circular wait. Primary implementation: [DVDVideoCodecAndroidMediaCodec.cpp, Kodi 21.3](https://raw.githubusercontent.com/xbmc/xbmc/21.3-Omega/xbmc/cores/VideoPlayer/DVDCodecs/Video/DVDVideoCodecAndroidMediaCodec.cpp).

A software-decoder-only candidate was insufficient: cancellation while the plug-in URL still resolved produced a separate YouTube invoker termination/hang. The repaired lifecycle therefore resolves the stream before giving Kodi a playback request.

The repeated navigation check also exposed an existing Back bug on YouTube Home: generic page handling reloaded Home instead of opening the sidebar. The repaired Home action opens the sidebar; other YouTube tabs return to Home, and nested folder history retains precedence.

## Maintained repair

- Resolve decorative previews on a background worker through the existing serialized native YouTube SDK runtime. Cancellation invalidates the result before playback; only prepared HTTP(S) streams enter Kodi's playback queue. Full-video click playback keeps its native route.
- Preserve native playback ListItems and buffer player properties/notifications until dispatch. Keep local and remote history reporting disabled for previews and retain the native 30-second preview end marker.
- On Android, use software decoding only for owned decorative previews. Journal both original decoder booleans before changing either; restore them on cancellation, normal-play transition and restart recovery. Accept the legacy one-setting recovery record.
- Serialize preparation, dispatch and cancellation/restoration under the same ownership lock. Generation checks also abort a reentrant acquisition after restoration. Review reproduced a two-setting race in the earlier candidate; regression tests failed before this correction and passed afterward.
- Keep artwork, watched/progress logic, account grants, quality choices, buffers and normal-video playback settings intact.

## Regression and native acceptance

All 569 controller tests pass. New regressions cover queued-resolution cancellation, stale results, deferred native effects, decoder recovery and partial failures, concurrent/reentrant cancellation, and YouTube Back navigation. Independent code review found the decoder restoration race and confirmed its correction.

Final native acceptance and restart/preservation receipts are recorded in `controller-source/youtube-stall-native-verification.json` once the run is complete. Raw traces, exact software/profile recovery archives and diagnostic scripts remain private in the task workspace `work/youtube-stall-2026-10-17/private/`. They contain account material and must never be packaged or published.

## Acceptance limits and release follow-up

This verifies targeted preview cancellation and browsing on this Fire Stick. It does not establish universal streams, long-duration playback stability, every codec/resolution, or a network throughput improvement. The normal-playback decoder check uses an anonymous 720p H264 fixture; no personal title or Trakt progress was changed. Software preview CPU cost can vary by stream; the observed Kodi UI FPS is a sample, not a CPU benchmark.

Release1.1.9 advances maintained tools to manifest76 and requires matching Fire/Mac native receipts before either clean edition verifies. Historical75 visual evidence is explicitly identified and usable only for unchanged layout/media/artwork source. No Apple TV test or rollout is implied.

## Recovery

Private `software-before.zip` archives contain the exact source preceding each software-only application; `before-manifest.json` records hashes. The native updater verifies the archive, owned addon roots and installed manifest before replacement, and verifies exact source afterward. It never restores an entire stale profile or overwrites refreshed grants. The final source includes the ordinary product entrypoint, without the temporary startup hook. The decoder recovery journal remains the production mechanism for an interrupted preview; remove it only after both original settings restore successfully.
