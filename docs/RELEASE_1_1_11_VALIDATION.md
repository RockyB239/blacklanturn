# BlackLanturn 1.1.11 validation

Both General and Apple TV & Mac editions contain controller 0.1.82 and unchanged Installer 1.0.16. The existing OpenWizard, GitHub Releases and Pages architecture, schema 3 playback-trakt-youtube-1 policy, managed Helper repairs and hash-pinned sanitized 1.1.2 baselines are retained. No personal profile is a packaging input.

## Category diagnosis and repair

Broad Education, Knowledge and Science-and-Technology classifications did not distinguish narrow shelf subjects. Native sampling found loosely grouped original shelves and broad related results crossing subjects. Recognized Science, History, Ancient History, Electronics, Philosophy, Psychology, Nature, Mysteries and other subject rows now require positive public-title or specific-topic evidence. Broad Knowledge/Education metadata, creator names and description boilerplate do not establish relevance. Music/Gaming/Sports checks remain included. Original videos, native continuations, related additions and playlist directories are screened; accepted cards retain native URLs, artwork, watched state and personalized order. Related seeds come only from accepted originals. No fixed searches or new recommendation service replace the account feed.

Ambiguous names have counterexample coverage: Roman Reigns is not ancient Rome, Samsung Galaxy reviews are not astronomy, Autodesk Maya is not ancient Maya, and a murder investigation is not investing. Playlist directories require their own title evidence. Metadata retains only bounded public classification/title fields in the existing account-owned cache. Existing identity retirement, cancellation and Retry behavior is retained.

This reduces mismatch rather than guaranteeing semantic accuracy. Ambiguous relevant titles can be skipped, and a shelf with no confirmed original choices can be hidden. Generic/format/unrecognized rows such as New to you, podcasts and recently uploaded retain provider-defined mixtures. Some cross-topic overlap is legitimate. YouTube failures can still require Retry or Refresh.

## Fresh installed-device results

| Device | New subject rows | Added matching choices | Tested subjects |
|---|---:|---:|---|
| Fire Stick | 1 | 5 | Science |
| Mac | 2 | 21 | Science, Consumer Electronics |
| Apple TV | 2 | 9 | Science, Mysteries |

Each new subject row exercised three continuation requests. All tested rows had zero policy mismatches; representative public titles were separately reviewed. Native remote navigation and Refresh recommendations passed. Continuation retained each original card prefix exactly, including artwork, watch state and ordering; Refresh generated a fresh provider recommendation set and may intentionally change that order. YouTube playback history remained unchanged.

All three devices have exact 311-file controller 82, ordinary startup and no diagnostic entrypoint hook. Fire 13 protected files, Mac 27 protected files, Apple 24 protected files and 21 persisted Apple preference entries passed exact or justified runtime-equivalence comparisons. Authorization grants, selected accounts and playback preferences were preserved; no profile reset or recovery snapshot restore occurred. Routine YouTube access-token renewal retained the existing grants. Owned staging was removed. Apple TV Screenshot builtin was not used.

The first Apple native feed supplied no new subject shelf. A separate fresh native Home run supplied Science and Mysteries and passed; this does not claim recovery of an exact earlier shelf. Native tests update existing profiles rather than perform clean installs.

## Source and release gates

The new real receipt is controller-source/youtube-release111-verification.json, pinned to manifest82. It requires fresh source/startup/settings/authorization/history proof, Refresh verification, continuation card preservation, a new subject row and continued choices on each device. Historical controller 81 playback/quality proof remains separately labeled in youtube-release110-verification.json and is accepted only while exactly addon.xml, youtube_home.py, youtube_provider.py and youtube_relevance.py differ, with no added/deleted controller paths. Playback, decoder, preview and layout implementations were reviewed unchanged. No fresh82 playback-quality or sustained 4K benchmark is claimed.

649 controller, 216 installer/release and 16 device-validation tests passed (881 total). Both reproducible payloads pass exact-source, wrapped-installer, clean-default, dependency, CRC and native-receipt verification. Compared with 1.1.10, each payload changes exactly six paths: the four controller paths plus the build marker and README; all other payload bytes are identical, including playback defaults and Installer 1.0.16. Private-account/payload scope checks pass.

- `BlackLanturn-General-Kodi21-1.1.11.zip`: SHA256 `9f998e8914f8db61e623252ae0ebb406f814ed9813277fda6b183ba224ba4b42` (90872685 bytes).
- `BlackLanturn-Apple-TV-Mac-Kodi21-1.1.11.zip`: SHA256 `62498af7113256b91f63440c50191e53d5c7a669d7b0e573b72f17f53ec4ea3b` (91688320 bytes).

Run from this repository:

```sh
PYTHONPATH=controller-source/addon python3 -m unittest discover -s controller-source/tests -q
python3 -m unittest discover -s tests -q
python3 -m unittest discover -s tools/device_validation -p 'test_*.py' -q
python3 tools/build_release.py --baselines ../../helper-managed-release-1.1.2/anonymous-downloads --output ../../youtube-topical-tuning-2026-10-18/artifacts
python3 tools/verify_release.py ../../youtube-topical-tuning-2026-10-18/artifacts
git diff --check
```

Independent CI must rebuild the exact accepted payloads before publication; live catalog/setup, repository XML/MD5/ZIP, unchanged wrapped Installer 1.0.16 and anonymous build downloads must match accepted bytes. Actual publication and CI receipts are retained in the local release task completion record.

## Preservation and recovery

Installer 1.0.16 is unchanged. Standard updates retain supported playback/language/Trakt/provider/artwork/buffer settings, 18 YouTube playback choices, 2 Android decoder choices and 3 Umbrella HDR/Dolby Vision/HEVC filters plus selected authorizations. Account-only clean mode uses build defaults and selected accounts. Existing automatic fullscreen quality up to4K and 45-second capped/fading previews remain unchanged. Prior 1.1.10 assets, installer ZIPs and private per-device recovery copies remain retained. Use software-only rollback where appropriate; do not replace current grants with stale profile snapshots. Wider devices, full Apple TV clean-install, Intel Mac and sustained 4K acceptance remain unproven.
