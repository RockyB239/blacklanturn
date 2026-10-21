# Release 1.1.16 validation

Status: validated source and local packages; publication/readback recorded below when completed. This is not a Fire Stick installation receipt.

## Scope and behavior

Both existing editions package Controller0.1.85 and skin0.1.39 with the native-tested Mac YouTube end-screen candidate. Signed-in Watch Next requests use the existing account and fall back to related results; identical YouTube.com ranking is not claimed. Three suggestions appear after a natural ending when ready. Recommendations load near the end without blocking playback startup or waiting at EOF. Suggestions default On, autoplay Off. Optional autoplay waits15 seconds; keyboard, pointer and focus navigation cancel it. First Back hides suggestions, second Back restores browsing. Details, local My Stuff and channel navigation are retained.

The user explicitly requested public build publication so they can install and test the Fire Stick at a hotel where direct access failed. No Fire Stick or Apple TV access or installation is performed in this release. New native feature acceptance is Mac only. Historical three-device and natural-episode/season receipts remain immutable evidence for their retained implementations; they do not certify this new delta. Sustained playback and formal before/after performance benchmarking were not run for the new feature.

## Source and package integrity

Manifest85 binds all314 controller files to the complete native-tested candidate snapshot, allowing only the controller addon version84→85 change. The Home.xml override hash is bound to the same native receipt and is applied to both editions after checking immutable baseline Home and skin metadata hashes. Skin metadata advances38→39, with all other skin files retained. The historical manifest84 and exact historical addon metadata remain available for prior natural-episode acceptance.

Reproducible packages start from the same hash-pinned sanitized1.1.2 baselines, never a personal profile. Build1.1.16 preserves the managed Helper/Umbrella/network fixes, platform-specific YouTube code, playback defaults, source-choice policy, artwork, language/subtitle and four-rating defaults. Clean controller defaults explicitly add YouTubeEndSuggestions=true and YouTubeEndAutoplay=false. Standard restoration still retains the exact original bounded rows.json, including existing/unknown preferences and saved items. Installer1.0.21 and Repository1.0.6 remain current. Installer21's existing ZIP is reused byte-for-byte after checking every member against maintained source, preventing a second archive under the same version.

The installer policy and preservation code are unchanged. Standard captures supported playback/Trakt/YouTube/codec/provider choices and selected Trakt/debrid/login authorizations before cleanup; unknown managed sources fail before cleanup. Preserve full Kodi GUI settings, sources, favourites, advancedsettings and playercorefactory through their existing Save Data switches when wanted. Account-only reset intentionally resets preferences and is not the requested mode. Other unselected local data is not promised preserved; cloud watched/progress is separate from local databases.

## Validation

- 698 controller tests passed.
- 577 installer/release tests passed, including full deterministic rebuild contracts and five new end-screen release guard tests.
- 36 source-selection/playback lifecycle and16 native-probe tests passed.
- New negative cases reject source drift, missing Mac behaviors, an early countdown, a false remote-device claim and unknown skin source.
- Native Mac end-screen tests include real natural EOF and autoplay, Back cancellation with more than16 seconds idle, direct return with suggestions disabled, pointer-focus cancellation, details/local save-remove/channel return, ordinary restart and matching installed source. 280 core preferences and301 protected files passed preservation, allowing only operational normalization, normal short-lived access-token refresh and the three test-play YouTube history entries. Private raw receipts stay private; sanitized source-bound acceptance is controller-source/youtube-end-native-verification.json.
- Independent focused package review found no important or blocking findings. Its minor historical README version typo was corrected before freezing release artifacts.

Final hashes, delta/privacy checks, CI and public readbacks are recorded after verification. Prior releases and private recovery copies remain retained. Roll back through a retained earlier build using the same Standard preservation choices; do not restore an old whole personal profile over current account tokens.

## Frozen artifacts and local gates

- `BlackLanturn-Apple-TV-Mac-Kodi21-1.1.16.zip`: SHA256 `f171f3f2bf1c03420746f8959133c8fb87580685003bd5f8166a104357db9ad8`, 92052478 bytes.
- `BlackLanturn-General-Kodi21-1.1.16.zip`: SHA256 `84e5fdcc80f4b950dd16c0edf7d67bd2e92045810a5c1c889a2e528cde320c98`, 91236934 bytes.
- `plugin.program.blacklanturninstaller-1.0.21.zip`: SHA256 `1850230644b8a1f5373f9990aaf715ad4715fcdf9851878877fbdfa345003213`, 3927837 bytes.

Both editions have exactly18 changed paths relative to anonymously verified public1.1.15. The remaining source, platform workarounds and all userdata except release marker/README/two clean controller defaults are byte-identical. Installer21 ZIP is exact. The complete package verifier passed; deterministic rebuild contracts passed. Known-private-value scan checked16 private values plus one excluded already-public baseline default across changed source and all three archives, with no findings. No personal files are packaged.
