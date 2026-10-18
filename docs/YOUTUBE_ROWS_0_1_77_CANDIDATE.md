# YouTube rows and recommendation refresh — candidate 0.1.77

YouTube rows now retain and follow the connected account's native feed and shelf continuation context. A focused row prefetches when about five cards remain. Finite rows stop at the end; failed requests retain the current cards and offer Retry. Next provides an explicit fallback and advances to another bounded window after approximately 150 retained items. YouTube paging cards omit the generic Browse more titles caption.

Category additions prefer videos that have appeared in fewer than two other category rows. This is a soft preference: small real categories remain usable. Existing cards, artwork, watched metadata and selection stay stable while a batch arrives. Playlist navigation returned by a shelf is retained.

Refresh recommendations appears below the final YouTube Home category and in its context menu. It requests fresh main feeds and personalized shelves, bypassing their relevant caches without deleting account or history stores. New rows and categories replace the old Home together. Failure retains the old Home. Explicit folder/details navigation retires the request; ordinary movement among Home rows remains supported. YouTube may recommend the same videos again.

## Validation

- 591 controller, 193 installer/release and 16 native-probe unit tests passed.
- Actual Mac Kodi 21.3: main feeds expanded from 50 to 100 videos; two personalized shelves expanded through their own cursors. Existing selection, artwork and watched metadata were retained.
- Finite-row end, vertical navigation, Retry, keyboard access to the bottom button, context-menu refresh and failed-refresh retention passed.
- Full Home refresh took 9.946 seconds in the final run. Account responses supplied 17 Home rows. These are bounded Mac observations, not cold-load or Fire Stick performance guarantees.
- Exact-video windowed preview with history reporting disabled stopped in 0.424 seconds using external navigation. No native UI polling ran inside Kodi's Python process during shutdown. Earlier intrusive probes and their failures were retained; their stop timings are not acceptance evidence.
- All 27 protected Mac settings/account files remained byte-identical or semantically equivalent. Only normal XML/runtime telemetry and YouTube access-token renewal differed. Grants, selected accounts, playback preferences and local YouTube history were preserved.
- Ordinary restart loaded both Home rows, had no active player, and matched manifest77 exactly with no diagnostic hook.

The sanitized receipt is `controller-source/youtube-rows-mac-verification.json`. Candidate source integrity is pinned by `controller-source/manifest77.json`; this is not Fire Stick release acceptance.

## Distribution boundary

This candidate is installed on the Mac only. Apple TV and Fire Stick were not accessed. The published build 1.1.9 and Installer 1.0.15 are unchanged. Their release builder remains pinned to manifest76 and rejects this candidate until a separately validated promotion updates the release inputs. Reproduce the published release from tag `v1.1.9`.

Keep the initial device controller archive for recovery. Restore only the controller folder during an idle normal Kodi restart; do not restore stale whole-profile settings or authorizations. The local task retains a verified controller-only rollback script and private recovery archives.
