# Personal library release 1.1.38

Controller 0.1.102 and Installer 1.0.42 retain the current managed add-ons, platform-specific variants, compatibility fixes and both icon packs. The personal Fight Zone add-on remains excluded from public distribution.

Includes local personal collections, named saved searches preserving category, movie-franchise release order and next released unwatched title, and optional suggestions after the last currently available episode. A different series never autoplays. Local-shelf status is refreshed from the existing watched/resume cache; metadata is copied once before rendering.

Native playback integration identified and fixed missing JSON episode fields by consulting only the active player's actual episode tag and rejecting contradictory observations. An established session is retired if playback becomes unidentifiable, so prior suggestions cannot follow an unrelated stream.

Validation: 1,056 Controller and 938 installer/update tests; six isolated native clean/Standard/full-update cases and two component-update cases; four actual Kodi player/dispatcher/window/worker/dialog/browsing-return cases for natural episode EOF, Stop, nonfinal episode and disabled suggestions. Provider results are controlled fixtures using freshly recorded public metadata and local test media, with network and personal-profile access denied. No full real-service finale or physical clean Android/tvOS install claim. Mac text entry passed; Apple native remote/phone text entry remains unverified at user direction. Initial harness setup failures were not accepted as passing evidence.

Standard preserves personal collections, named queries and preference switches; true Update BlackLanturn leaves all existing saved data and unrelated add-ons in place. Frozen older manifests/artifacts remain unchanged. The prior historical129 playback source is retained verbatim under its original SHA, avoiding comparison of old releases against new code. New release text is validated before a full payload is emitted. CI builds both editions from pinned published37 baselines.
