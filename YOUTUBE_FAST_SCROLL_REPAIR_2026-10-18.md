# YouTube row navigation repair — 2026-10-18

Controller **0.1.79** is installed and verified on Fire Stick, Mac, and Apple TV. Published build **1.1.9** and Installer **1.0.15** remain pinned to controller76. No publishing or installer replacement was performed.

The Fire Stick reproduced the reported lockup: a queued row reset left dispatched native focus at0, with51 visible/model cards and a live monitor. The first synchronous-focus correction also failed natively. The corrected dispatched check passed8 consecutive external Select+24 rapid-Right bursts through the bounded row reset. It preserves intentional moves to other controls and revalidates ownership after dispatch.

Other confirmed defects: the150-item automatic limit suppressed explicit Right; redraw failure could leave the global request occupied or consume a terminal cursor before committing the new cards; public playlist images used the200px local icon layout; the Next graphic ignored Retry item labels. The repair retains retryable cursor/model state, releases only the owning job, clears stale end signals on row-window changes, and uses the full landscape layout for public playlist thumbnails. Local Shorts/Live icons keep their centered treatment.

## Fresh validation

| Device | Home rows | Continuation batches | Real Retry after controlled redraw failure | Restart/source/preservation |
|---|---:|---:|---|---|
| Fire Stick |17|27|Pass|309 exact files;13 protected files preserved|
| Mac |17|26|Pass|309 exact files;27 protected files preserved|
| Apple TV |17|26|Pass|309 exact files;24 protected files and21 persisted preference entries preserved|

Fire screenshot `work/youtube-fast-scroll-2026-10-18/private/fire/final2/row-2.png` (project workspace) was inspected: StarTalk and other real playlist thumbnails fill their cards. Native full-card playlist render properties also passed on all devices. No Apple TV screenshot builtin was invoked. Fire/Apple owned task staging was removed; installed entrypoints have no diagnostic hook.

The Mac's first run received one server response without continuation content and displayed Retry. A complete fresh Home rerun passed. Recovery of that exact earlier server cursor was not established, and no unsupported provider workaround was added. Finite rows stop when YouTube has no continuation. This is bounded navigation verification, not a long-duration soak or a new performance benchmark.

## Maintained source and tests

Source: `controller-source/addon/`.
Manifest and sanitized acceptance receipt: `controller-source/manifest79.json` and `controller-source/youtube-fast-scroll-verification.json` inside that repo.

From the maintained repo, the following checks passed:

```sh
PYTHONPATH=controller-source/addon python3 -m unittest discover -s controller-source/tests -q
python3 -m unittest discover -s tests -q
python3 -m unittest discover -s tools/device_validation -p 'test_*.py' -q
git diff --check
```

Expected counts:605 controller,193 installer/release,16 device-validation tests; no failures. Independent read-only review approved the final patch and verified all309 source hashes against manifest79.


Local recovery and candidate package: `work/youtube-fast-scroll-2026-10-18/` in the project workspace.
