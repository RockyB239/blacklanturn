# Native Kodi acceptance probes

These probes execute inside the existing controller startup interpreter under a private, per-run recovery guard. They are not addons or build payload files. Stage both native scripts beside the owned guard; set DEVICE_NAME and optional SHARED_DEADLINE globals when executing native_benchmark. Reports stay in that private staging directory. The paging probe covers3ordinary Next/Previous cycles,30repeat prepared-page cycles, pending-preload cancellation where observed, full artwork/watch/resume preservation, and returnHome.

Use only an idle device after exact software and protected-profile backups have been verified. Recover source on any failure/interruption, then restart Kodi to discard diagnostic method wrappers. Never publish generated reports or recovery archives; they may include personal viewing metadata.

All native label snapshots use XBMC.GetInfoLabels, dispatched through Kodi's GUI message loop. Do not replace this with xbmc.getInfoLabel from the background acceptance thread: the former reader reproduced a native list-item crash while Home replaced artwork. Native metadata fields and model ownership checks must remain intact.

Run platform-independent checks from repository root:

```sh
python -m unittest discover -s tools/device_validation -p 'test_*.py'
```

Successful short runs prove only the reported workload, never universal absence of native crashes or full provider playback. Use a fresh per-run identity and retain exact script/source manifests with the native receipt.
