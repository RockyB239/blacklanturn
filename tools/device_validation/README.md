# Native Kodi acceptance probes

These probes execute inside the existing controller startup interpreter under a private, per-run recovery guard. They are not addons or build payload files. Stage both native scripts beside the owned guard; set DEVICE_NAME and optional SHARED_DEADLINE globals when executing native_benchmark. Reports stay in that private staging directory. The paging probe covers3ordinary Next/Previous cycles,30repeat prepared-page cycles, pending-preload cancellation where observed, full artwork/watch/resume preservation, and returnHome.

Use only an idle device after exact software and protected-profile backups have been verified. Recover source on any failure/interruption, then restart Kodi to discard diagnostic method wrappers. Never publish generated reports or recovery archives; they may include personal viewing metadata.

All native label snapshots use XBMC.GetInfoLabels, dispatched through Kodi's GUI message loop. Do not replace this with xbmc.getInfoLabel from the background acceptance thread: the former reader reproduced a native list-item crash while Home replaced artwork. Native metadata fields and model ownership checks must remain intact.

Run platform-independent checks from repository root:

```sh
python -m unittest discover -s tools/device_validation -p 'test_*.py'
```

Successful short runs prove only the reported workload, never universal absence of native crashes or full provider playback. Use a fresh per-run identity and retain exact script/source manifests with the native receipt.

## tvOS virtual XML safety

Use `native_storage.listdir(vfs, directory)` for native settings directory listings and `native_storage.read_xml(vfs, path)` for read-only XML diagnostics. A local directory passed to `xbmcvfs.listdir` without its trailing slash can omit tvOS XML and cache it as missing. A later XML read can return zero bytes even while `xbmcvfs.exists` returns true. Never interpret that result as permission to initialize, reset or replace an existing settings file. The safe reader primes the correctly terminated directory and rejects unreadable/invalid XML without writing it.

Kodi runs optimized Python. Use explicit conditions or `native_storage.require`; do not use `assert` for native validation or for operations with side effects.

For the maintained Apple TV regression, stage `native_storage.py` and `native_storage_probe.py` together under an existing idle-device entrypoint/rows recovery guard. Run the probe as a separate script interpreter. Its deliberately unsafe listing is confined to a UUID-owned fake settings directory. Never substitute an actual addon profile or the userdata root. Real GUI, Helper and Umbrella XML is only read and checked unchanged. Keep a private full-profile recovery snapshot and compare all persisted userdata entries on the host as well. The probe is specific to the reproduced Kodi21.3 tvOS behavior; rejection on a different platform is not evidence of a new reset.

This guard fixes the maintained diagnostic path. It does not patch Kodi itself or guarantee safety for unrelated addons that issue unsafe listings. See [the incident analysis](../../docs/TVOS-SETTINGS-CACHE-INCIDENT.md).
