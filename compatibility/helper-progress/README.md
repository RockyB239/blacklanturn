# Helper 6.17.9 playback-position candidate

Local candidate only. No profile, device, credentials, settings, release version,
manifest, payload, hosting or update rule was changed by this candidate task.
Native attribution of the final Trakt writer and device acceptance remain separate
release gates. The current managed empty-cache/search changes are independent.

## Exact baseline

Each file was copied directly from
`compatibility/helper-empty-cache/upstream-6.17.9.zip`, member prefix
`addons/plugin.video.themoviedb.helper/resources/tmdbhelper/lib/monitor/`.

| File | Upstream SHA-256 |
| --- | --- |
| scrobbler.py | 41c14fcb319807aedec1aad9e43408d0d4e3f00e053cad4ea8390d3bf95af7c3 |
| player.py | 079edde05adceebe5a8cb7aafab02b1e5fbadfed0c8165db9d3f3d92a7606424 |
| service.py | be6dbaa4855e25f644d45f4c23ef3934323095f4e87d3a528e08f81d0a56473a |

Candidate files replace those same three paths when explicitly integrated; they
do not replace the shared Poller, image monitor, or other upstream files.

## Source defect and bounded change

Upstream derives playback position from wall time since the last callback sample.
Its regular fullscreen loop only refreshes position after 80 percent, and Stop
often arrives after native timing is gone. A missed seek sample therefore leaves
elapsed viewing time as progress. A pause also advances inferred progress while
Kodi's actual position remains fixed. Seek callback spelling is already correct.

The candidate retains the last valid Kodi sample. Samples must be numeric, finite,
not boolean, and between zero and the session's duration. Invalid or unavailable
samples preserve the previous position. Start, pause, stop, and fullscreen sync retain their session
reference across a timing read; native timing RuntimeError is tolerated during
updates and the existing fullscreen threshold check.

The seek callback validates and retains Kodi's absolute callback position
(milliseconds converted to seconds) before its existing one-second settling wait.
Stop during that wait therefore retains the seek position. The post-wait actual
timing refresh runs only when the same session remains live; an old seek callback
does not start a replacement session.

ServiceMonitor's existing idle loop samples locally at most once per second,
including windowed/background playback. The deadline persists across short UI
waits. Only a live, unstopped scrobbler takes this path. With no live scrobbler,
the original idle wait runs unchanged, without reading the monotonic clock or
native player. Long playback waits remain abort-responsive. Session removal ends
sampling and restores the remaining idle wait. Replacement by another live
session continues sampling at the existing global deadline. No new thread or shared Poller
change is used. Sampling does not call a Trakt/MDBList endpoint; existing auth,
identity, start/stop and 80-percent sync rules remain in place.

Expected Stop precision is the last successful sample, normally within one second
of Kodi's position while the service loop is running. Work that blocks the existing
service loop can delay sampling; failed reads intentionally retain the prior valid
sample. Native validation must check the outgoing writers and final settled cloud
value before release integration.

The original audit's approximately 12-versus-2.5-percent mismatch is intermittent.
A later native original-source seek/pause/resume/Stop trace accepted the seek and
reported approximately 12 percent from both writers. These unit regressions prove
the specific source defects and candidate behavior; they do not independently
attribute the historical final writer or replace native candidate acceptance.

## Reproduce the red/green evidence

From the repository root:

```sh
HELPER_PROGRESS_UPSTREAM=1 python3 -B -m unittest discover -s tests -p test_helper_progress.py -v
python3 -B -m unittest discover -s tests -p test_helper_progress.py -v
python3 -B -m unittest discover -s tests -v
```

The test loader executes the actual three source modules and the actual upstream
Poller. Only external Kodi/module boundaries are faked. No installed add-on or
network is used. Assertions use literal expected positions and request counts.

Initial RED, before any candidate behavior change: 9 tests, 10 assertion failures
and 3 runtime errors. Missed-seek Stop emitted 2.4317121918720854 percent rather
than 11.95869420386409; pause advanced 718 seconds to 1318 seconds; getTime errors
escaped; the idle loop performed no samples. Added callback replacement and
fullscreen timing-race tests were separately observed failing before their fixes.
Review caught a live-session replacement being treated as disappearance. Its
regression failed with the replacement position still zero after a five-second
idle; re-evaluating the current live session after each wait corrected it without
resetting the sampling deadline or adding network calls.
The quick-seek/Stop regression then failed against the earlier candidate with
0.4663557628247834 percent instead of 10.00058294470353 percent. A separate
replacement-session regression observed the old seek callback starting the new
session. Both passed after retaining callback position before the settling wait
and guarding the subsequent refresh by session identity. Paused Stop without any
resume is explicitly covered: a 600-second pause adds zero position progress.

Final repeated evidence on 2026-10-18:

```text
RED upstream: exit 1
Ran 19 tests
FAILED (failures=16, errors=8)

GREEN candidate: exit 0
Ran 19 tests
OK

Repository root suite:
Ran 251 tests
FAILED (failures=1)
```

The root-suite failure is
`test_repaired_search_release.RepairedRelease.test_controller_has_reviewed_repair_and_preview_safety`:
the controller manifest does not match concurrent controller-source edits. Those
integration-owned files were not changed by this task.

Coverage includes a missed seek followed by local polling and Stop with native
playback already false (718/6004 seconds = 11.95869420386409 percent), a ten-minute
pause without drift, timing errors, invalid samples, identity rejection, sampling
rate, no extra Trakt requests, exact nonplayback idle bypass, abort response,
session disappearance/replacement, retained 80-percent sync and auth denial.

Recovery before integration is to omit these candidate files. After an explicitly
authorized integration, restore the three exact upstream members or the saved
pre-integration copies and reverify hashes; this task did not perform deployment.
