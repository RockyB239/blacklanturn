# Release1.1.9 acceptance

Both General and Apple TV & Mac editions include the exact308-file controller0.1.76 stall repair and wrapped Installer1.0.15. Installer executable logic is byte-identical to1.0.14; only addon version metadata changes. Policy schema3, playback-trakt-1, minimum Installer1.0.13, managed Helper empty-cache-1/search-batch-1, update protection and per-edition/native-component exclusions remain intact.

## Native evidence

Fire Stick acceptance comes from the exact source committed in d004cd1. Queued resolution, opening and playing cancellation passed, with Home returns2.201/2.513/1.380seconds, no late playback, and both normal decoder choices restored. The preview used ff-h264; normal anonymous720p H264 playback used amc-h264 afterward. Four navigation rounds, six searches, two YouTube cycles, ordinary restart and exact installed-source audit passed. All13 protected settings/account files were preserved semantically and local YouTube history hashes were unchanged. Temporary Fire diagnostics were removed. See controller-source/youtube-stall-native-verification.json and docs/YOUTUBE-STALL-FIRE-0_1_76.md.

The same exact controller76 was freshly installed on the idle Mac after private source/settings recovery copies. Native signed-in feeds matched50 recommendation and50 subscription video IDs; connected/disconnected/reconnected/transient visibility, account-scoped return, all tabs, search, channel navigation, adaptive15 interest rows, watched refresh preserving artwork/order, folder tiles, preview toggle and exact selected-video preview passed. Local and remote history-reporting flags were disabled, preview end was30seconds, selection change stopped playback in0.206seconds, and local history was unchanged. An ordinary restart loaded Home with both rows ready; exact source and all27 settings/account files matched, allowing only XML order, uptime/peripheral activity and YouTube access-token renewal. Authorization grants/selected accounts and playback choices were preserved; refreshed tokens were retained.

The restart diagnostic initially assumed Fire window13000; live Mac GUI identity proved window13001 was already Home/ready. The audit was corrected to read current-window properties. This was a diagnostic error, with no product change. The ordinary restart and final audit passed.

Prior explicit visual observations are identified as controller75 evidence and retained only because all layout, font, media and artwork files are byte-identical. Current76 native model/card/navigation/preview checks were rerun. The gate compares the full prior manifest and rejects changes outside addon.xml, live_review.py, preview_geometry.py and youtube_provider.py; fresh visual acceptance is then required. No75 full-source receipt is misrepresented as76 testing. New source proof: controller-source/youtube-stall-mac-verification.json.

Apple TV was not accessed, restarted, tested or updated. The Apple TV & Mac distribution package is updated; that does not deploy it to the personal Apple TV. No new full Apple TV clean-install acceptance is claimed.

## Reproduction and durable gates

The release tools now require manifest76 for both packages plus matching Fire and Mac native receipts. Regressions reject missing cancellation stages, unrestored decoders, lost history/settings, stale source, missing ordinary restart and unverified visual-source changes. Verification retains prior broader YouTube acceptance checks as identified historical coverage. Tests passed:569 controller,193 installer/release,16 native-probe.

Both deterministic payloads are rebuilt from hash-pinned public1.1.2 clean baselines, never live userdata. Relative to the prior1.1.8 assets, each contains exactly seven changed paths: four controller files, installer addon.xml, build marker and build README. All other bytes, including playback/Trakt/buffer/artwork defaults and sanitized account-free userdata, are unchanged. No credentials, histories, databases, native binaries, device overrides or recovery material are included. The installer source diff is version-only; preservation behavior is unchanged and tested.

## Distribution and recovery

The existing GitHub release-asset and Pages catalog architecture is retained. The new versioned release assets are BlackLanturn-General-Kodi21-1.1.9.zip and BlackLanturn-Apple-TV-Mac-Kodi21-1.1.9.zip, with Installer1.0.15. Older releases and installers remain available. Catalogs and repository XML/MD5 advance together only after package, privacy and CI verification; anonymous downloads must match accepted hashes before completion is reported.

Use Standard update with existing selected preservation options to retain preferences and authorizations. Account-only clean installation intentionally restores build defaults except selected account grants. No clean install or reset was performed on a personal device for this release. Fire's existing HDR/Dolby Vision/decoder choices remain its own normal-playback choices; software decoding is temporary for owned decorative previews, with journaled restoration on cancellation/normal playback/restart.

Exact source, immutable artifacts, scope/privacy results and hosted-byte receipts are retained in work/youtube-stall-release-2026-10-17. Private recovery archives remain private; do not package them. Roll back by selecting a retained prior release with the same preservation options, or restore only the exact backed-up software through the existing guarded updater. Do not overwrite current authorization files from an older full-profile snapshot.

Limits: existing caches were retained; row readiness does not mean every texture was drawn. These are bounded native checks, not a statistical speed claim, long-duration playback test, every-codec guarantee or independent remote-history API verification. Software preview CPU cost varies by stream. No Apple TV or Intel Mac runtime validation was added.
