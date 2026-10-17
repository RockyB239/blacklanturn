# Release 1.1.5 native validation

Status: native rollout gate passed on October 17, 2026. Controller 0.1.73 and Installer 1.0.12 are installed on all three tested devices. Publication follows verified release downloads and Pages metadata activation.

## Crash diagnosis and repair

The unchanged 0.1.72 candidate reproduced a native Fire Stick crash after 30 prepared-page replays, when Home replaced its rows. The faulting Python frame was the diagnostic reader's direct xbmc.getInfoLabel artwork query. The native stack ran through GetMultiInfoLabel and list-item destruction; another thread was constructing row cards. This establishes the reproduced unsafe boundary and supports a concurrent ownership race. It does not prove every earlier historical allocator failure had the same cause.

Maintained native probes now take coherent metadata snapshots through GUI-thread JSON-RPC dispatch. Controller 0.1.73 routes its similar label reads through that dispatcher and revalidates row and preview ownership after waits. Preview alignment retains the cancellation lock. The 0.1.71 preview retry safety is preserved; the rejected progressive-results implementation remains excluded.

## Native acceptance

| Device | Paging and cancellation | Restart/source audit | Protected settings/accounts |
| --- | --- | --- | --- |
| Fire Stick | Passed, 3 ordinary cycles + 30 prepared-page replays | Passed | 11 files |
| Mac | Passed, 3 ordinary cycles + 30 prepared-page replays | Passed | 22 files |
| Apple TV | Passed, 3 ordinary cycles + 30 prepared-page replays | Passed | 3 files; 21 persisted userdata entries also checked |

Each final run passed row loading, both tested search queries, embedded preview advancement and navigation cancellation, observed pending-preload cancellation, Home/sidebar recovery, exact rendered artwork/watch metadata comparisons and source verification. No native crash or unexpected runtime error occurred. Expected PageCancelled events are classified only inside the exact interval of a verified successful cancellation; raw events remain in private evidence. This timing correlation does not identify every request individually.

The metadata sample included a watched title and full artwork/playcount/resume fields. No nonzero in-progress resume fixture was available; no viewing history was fabricated. Tests retained existing caches and do not establish universal cold-start or provider/stream performance. These were targeted software updates, not fresh personal-device wipes.

Profiles, hardware-specific playback settings, authorizations and native playback components were preserved. The Mac performed a normal YouTube access-token renewal with unchanged account/refresh identity. Apple TV's gzip-backed persistent userdata was separately compared, excluding only the peripheral last_active timestamp; control values, playback settings and authorization values remained checked. Full private software/profile recovery copies are retained outside the public repository.

## Validation-tool findings

Earlier failed trial reports remain unchanged. The first dispatched reader exhausted its paging deadline because of excessive individual GUI round trips; coherent batching removed that overhead. A subsequent control passed the stress workload but classified deliberately cancelled requests as failures; the bounded classifier was corrected with regression tests. The first Apple deployment completed native acceptance but rolled back when the host mistook an empty pre-existing update-rule list for missing evidence. The collector now distinguishes missing evidence from an empty valid list. A further Apple retry was deliberately stopped through guarded recovery to correct peripheral timestamp comparison; the final complete run passed all gates. These were validation-tool corrections, not additional Kodi crash reports.

## Maintained release verification

480 controller, 119 installer and 10 native-probe regression tests passed; the unchanged Helper also retains its 12-case native cache regression evidence. Both reproducible payloads pass CRC, every-file manifest, exact maintained controller/Installer/Helper source, mandatory playback defaults and credential/native-binary exclusions. Installer 1.0.12 retains the complete managed Helper manifest and per-addon auto-update protection. Future reviewed Helper updates must use the maintained build/update process. Manually replacing Helper or enabling its upstream auto-update bypasses that protection.
