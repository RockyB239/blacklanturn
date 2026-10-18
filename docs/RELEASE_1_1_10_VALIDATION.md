# BlackLanturn 1.1.10 validation

Both General and Apple TV & Mac editions contain controller 0.1.81 and Installer 1.0.16. Release policy is schema 3, `playback-trakt-youtube-1`, requiring Installer 1.0.16 before cleanup. Existing older releases remain supported through their original policy; prior installers reject this new policy before native setup/cleanup.

The source is pinned by manifest81 (311 files) and the fresh sanitized three-device receipt `controller-source/youtube-release110-verification.json`. Historical 75/76 acceptance is retained unchanged. Builds use only the hash-pinned sanitized 1.1.2 public baselines and maintained source; no live profile, account database, history or recovery snapshot is packaged.

## Category diagnosis and repair

The previous related-video extension did not constrain broad watch-next recommendations to a category. Native Fire sampling found Pop Music's original five videos categorized as Music, while only eight of the next twenty broad related choices were Music. Original YouTube shelves can themselves be loosely grouped. Positive YouTube category/topic checks now cover recognized Music/Gaming/Sports labels, their original videos, continuation seeds, native continuation and related additions. Legitimate music uploaded under Entertainment remains eligible through music topics. Mixed/coarse labels such as History/Science/New to You remain native. This checks broad topic families, not perfect instrument/genre accuracy or a semantic guarantee about every uploader's classification.

Public taxonomy is fetched through the existing client in bounded batches with an account-owned cache. Removed/private/unclassified videos are skipped individually in valid responses; real service failures retain Retry. Identity retirement is checked before and after reads. Bare game-title text does not turn Game of Thrones or Squid Game into gaming shelves. No political-keyword blacklist, cookie authentication or new recommendation service was introduced.

## Fresh native results

|Device|Lower rows /batches|Preview media duration|Music rows /mismatches|Automatic fullscreen selection|
|---|---:|---:|---:|---:|
|fire|15 /45|45.34s|3 /0|1080p|
|mac|15 /44|45.09s|3 /0|1440p|
|apple_tv|15 /45|45.02s|2 /0|2160p|

All tested previews used H.264 at 720p or below, faded to artwork, ended without same-hover restart and had sub-second maximum probe gaps. Fullscreen selections used the same public NASA 4K source with an automatic 2160p ceiling through the real Play handoff. Fire queued/opening/playing cancellation passed, with five seconds of no-late-play observation after each resolver finished; normal core settings returned and subsequent local playback used `amc-h264` hardware decoding. YouTube playback history remained unchanged on all three devices.

Ordinary restart and exact source passed on all devices; installed entrypoints have no diagnostic hook. Protected comparisons covered 13 Fire files, 27 Mac files, 24 Apple files and 21 persisted Apple preference entries. Fire and Apple owned test staging was removed. Settings and authorization snapshots were never restored onto devices. Apple TV Screenshot builtin was never invoked.

One initial Mac MOBA native cursor returned acknowledged responses without continuation content even after Retry. Explicit Refresh generated a new recommendation set and the complete fresh run passed; the original cursor was not recovered. Real YouTube failures can still require Retry or Refresh.

## Quality defaults and update preservation

Clean installs explicitly enable adaptive video and automatic stream selection, set the 2160p ceiling, and retain baseline codec flags plus VP9. Inline previews independently cap 720p/H.264. Standard updates preserve 18 existing YouTube playback values, including explicit default-marked settings, quality/codec flags, audio-only/subtitle choices, both live-format selectors and five external/default-player routing booleans. Standard updates also preserve the existing Android decoder choices and Umbrella HDR/Dolby Vision/HEVC filters, even when Keep GUI is disabled. Authorization handling remains separate and unchanged. Clean account-only mode resets preferences to build defaults while retaining selected authorizations.

Installer tests exercise actual cleanup/extraction, clean defaults and Standard preservation, including long/empty codec lists, retry recovery and old-installer rejection. Existing buffer/artwork/language/forced-subtitle/Trakt/provider/native-component behavior remains retained.

## Build and verification

639 controller tests, 211 installer/release tests and 16 device-validation tests passed. Independent reviews approved category filtering and all 18 playback preservation keys. Both payloads differ from 1.1.9 in exactly 17 approved controller/installer/YouTube-default/readme/marker paths; unrelated payload bytes are unchanged. Privacy verification found no personal account fields or private recovery data.

- `BlackLanturn-General-Kodi21-1.1.10.zip`: SHA256 `f6406d268811c42deddb33530eb86d0482b6c3c90964d339dfe46b056e0916cb` (90870149 bytes).
- `BlackLanturn-Apple-TV-Mac-Kodi21-1.1.10.zip`: SHA256 `de5e0ce9b7f98b0fd3a65e47f5c073c27b287b43f43c0bea43a5cad1404feb76` (91685784 bytes).

From this repository:

```sh
PYTHONPATH=controller-source/addon python3 -m unittest discover -s controller-source/tests -q
python3 -m unittest discover -s tests -q
python3 -m unittest discover -s tools/device_validation -p 'test_*.py' -q
python3 tools/build_release.py --baselines ../../helper-managed-release-1.1.2/anonymous-downloads --output ../../youtube-category-release-2026-10-18/artifacts
python3 tools/verify_release.py ../../youtube-category-release-2026-10-18/artifacts
git diff --check
```

CI must independently rebuild the exact accepted artifacts before publication. Live catalog, setup, wrapped Installer and repository XML/MD5 must match the accepted tree after Pages deploys. Exact CI/publication/download receipts are retained in the local release task completion record.

Recovery: retain 1.1.9 assets, previous installer ZIPs and private per-device recovery archives. Use software-only rollback where needed; do not replace current profile/plist grants with stale snapshots. Personal devices were updated in place; full Apple TV clean-install, Intel Mac and sustained 4K throughput/frame-drop acceptance remain unproven.
