# Release 1.1.6 acceptance

## Diagnosed faults and corrections

Apple TV logged a UnicodeDecodeError from the Help text read under its ASCII default encoding. Controller 0.1.74 explicitly decodes the shipped file as UTF-8. The existing native text-viewer flow is retained. Preview-language choice already persisted correctly, but its description was static. The settings hub now renders the saved English-first or provider-order preference and refreshes immediately after selection.

The correct TMDb television identity 1413 returned a generic Season 1 Trailer whose actual public YouTube title was American Horror Stories Season 1 Trailer. American Horror Story and American Horror Stories are different shows. The controller now reads public title evidence only from YouTube's fixed official oEmbed endpoint; candidates must match an anchored selected-title alias followed by recognized trailer/season/year metadata. A generic provider label alone no longer approves playback. The selected show's identity-scoped original-title alias is supported; episode labels such as Pilot cannot override the show identity. Title collisions, sequel extensions, stale selection generations and cancelled queued requests are rejected.

Verification checks at most six ranked distinct video IDs, uses two concurrent network slots and an in-memory bounded title cache. Socket timeouts are two seconds; DNS and slow responses can take longer overall. Cancellation discards approval and prevents queued network work. Failed lookups are retried after a short 15-second negative-title cache; empty approved candidate lists are not retained in the controller preview cache. Unavailable or ambiguous evidence leaves artwork visible. This may omit legitimate trailers; it does not certify exact season, publisher authenticity or spoken language. No arbitrary URL or YouTube search fallback was added.

The Apple TV's preserved profile had Helper trakt_watchedindicators disabled. That option controls both incoming watched and resume enrichment. Enabling it and refreshing through the supported Helper route produced a nonzero resume point matching the same TMDb identity in Trakt (44.63 percent in both sources). Authenticated read-only cloud checks for user, playback and watched data returned HTTP200. This verifies the sampled incoming metadata, not every title or outbound scrobbling. No viewing history was fabricated.

The same profile used media-default audio and original-language subtitles. Only the requested incoming-metadata flag and two language settings changed across 21 persisted userdata entries; authorizations and decoder/HDR preferences remained intact. The packaged clean defaults are locale.audiolanguage=default (current Kodi interface language) and locale.subtitlelanguage=forced_only. System means Kodi's interface language here, not independent detection of the tvOS operating-system locale. Existing preserved preferences are not overwritten at startup. Forced-only behavior still requires correctly flagged forced subtitle tracks.

## Source and packaging verification

- 523 controller regressions passed, including actual Help decoding, native-handler selection/persistence, exact wrong-series identity, title collisions, transient failures and cancellation/cache ownership.
- 122 installer/release checks and 10 maintained native-probe regression checks passed.
- Independent code review rejected a preliminary substring match; the repaired anchored match passed fresh review.
- Both payloads were rebuilt from immutable verified 1.1.2 clean baselines, with exact controller 0.1.74 source manifests and identical managed software across editions. Installer remains 1.0.12, managed Helper remains its reviewed 471-file source; no upstream Helper source or update rule changed.
- Personal profiles, databases, authorizations, logs and foreign native components are excluded. Private recovery and diagnostics remain outside the repository.

## Native acceptance

Fire Stick acceptance passed before the same software was installed on Mac and Apple TV. All three then passed independent restart/source/preservation audits, with controller 0.1.74 and Installer 1.0.12. Each completed four section visits, six searches, a normally advancing embedded preview that stopped on navigation, three ordinary Next/Previous cycles, 30 prepared-page replays, observed pending-preload cancellation and Home recovery. No native crash or new runtime error occurred in these workloads. Each sampled 60 artwork/playcount/resume records, including one watched title. Nonzero resume records were unavailable in this paging fixture; the separate Apple cloud/directory identity comparison supplies the nonzero progress proof.

Protected files: Fire 11, Mac 22, Apple three physical files plus all 21 persisted userdata plist entries compared semantically (only peripheral last_active telemetry excluded). Fire/Mac YouTube access-token renewal occurred normally; account identities and all other protected values remained intact. Helper per-addon automatic-update protection remained enabled.

Focused native Apple checks passed: Help opened, accepted navigation and returned to settings; provider-order and English-first choices persisted and immediately rendered their correct description; the actual American Horror Stories video was rejected for American Horror Story and positively approved for its own identity. The requested runtime language settings and watched option were active. Twenty returned watched movie identities matched read-only cloud watched data. The original rows/configuration were restored exactly and Home was idle. A final independent persisted-preference comparison retained all 21 userdata entries. Two initial probe attempts exposed test-readiness and selection-dialog-ID mistakes; both recovered settings, and the corrected probe passed. Those were harness failures, not application regressions.

Both payloads retain exact accepted software and clean defaults. Package SHA256:

| Edition | SHA256 |
| --- | --- |
| General | 711a7164838bf0a8eb15e2c9896fb9019860657a35a53dfd14428241476b8394 |
| Apple-TV-Mac | 2b646e4953910481281e692f9453f9f629d4e7618e97191b7b64f59ed4bb0b99 |

Implementation references: [Kodi21.3 language handling](https://github.com/xbmc/xbmc/blob/21.3-Omega/xbmc/LangInfo.cpp), [stream selection](https://github.com/xbmc/xbmc/blob/21.3-Omega/xbmc/cores/VideoPlayer/VideoPlayer.cpp), and [official window IDs](https://github.com/xbmc/xbmc/blob/21.3-Omega/xbmc/guilib/WindowIDs.h).

## Limits and recovery

These are targeted software updates to existing devices, not another full clean installation. Wider Android/Intel Mac hardware, every provider/title and full outbound Trakt scrobbling are not certified. Previous immutable release assets remain available. Each device update retains exact private software and protected-profile recovery copies and restores software on acceptance failure.
