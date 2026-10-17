# Release 1.1.5 native validation hold

Status: staged only; do not merge this release branch to main or activate the installer catalog.

The first Fire Stick deployment acceptance on October17,2026 encountered a native Kodi crash while reopening a prepared page. Search, embedded preview and three Next/Previous cycles had passed. A repeat with Python fault capture passed the same workload and restart/preservation checks; it did not explain the first crash. A longer run completed12Next/Previous metadata comparisons without another crash, then failed its cancellation check at the fixed sidebar-navigation limit. Its later Home recovery succeeded. That run did not pass overall acceptance. Successful bounded repetitions are not evidence that the original native failure is fixed.

Mac and Apple TV have not been upgraded. Published build1.1.4/Installer1.0.11 remain active. The1.1.5 payloads and1.0.12 installer are prepared, with no release assets or catalog activation. Device authorizations and playback settings are outside the software-only update scope and are verified against private recovery snapshots.

The staged controller0.1.73 preserves0.1.71 playback safety and includes the repaired batched search/preloading sources;0.1.70 progressive delivery remains excluded. Managed Helper manifests and update protection are implemented and tested, but this does not waive the native rollout gate. Resolve the crash or obtain an explicit change to acceptance scope before publication.

## October17diagnosis

The instrumented unchanged0.1.72experiment reproduced a native crash in the diagnostic harness's direct artwork-label getter during Home replacement. Python/native stacks identify getInfoLabel -> GetMultiInfoLabel and list-item destruction; concurrent controller stack was building row cards. The faulting boundary is established; broader historical allocator-fault attribution remains limited. The maintained native probes now take coherent GUI-thread RPC snapshots. Controller0.1.73 hardens its caption/focus/decoder readers similarly and revalidates row/preview ownership after waits. Fire acceptance remains required before lifting this hold.
