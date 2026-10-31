# BlackLanturn 1.1.51

Recommended compatibility update: current add-ons with tested playback, tracking and saved-settings protection.

- Umbrella 6.7.99 and TMDbHelper 6.19.6 include the tested BlackLanturn playback, progress, search and reliability patches.
- Updated Trakt Sync 1.2.0, MDbList Sync 1.1.1 and Skin Variables 2.2.11. Kodi Sync 1.1.2 retains the local tracking support moved out of Helper by upstream.
- Installer 1.0.47 updates bundled add-ons and their reviewed patches together. MDbList migration preserves existing keys and intentional logout. Selected-account reinstalls retain new Floppy OAuth identity.
- Includes the accepted saved Home/section/row performance improvements, both icon packs, consistent YouTube folder artwork and Settings-only tracking controls.

Existing users: open BlackLanturn Installer and choose **Update BlackLanturn**. The required Installer update must finish first; restart Kodi if prompted. Use the in-place update to preserve accounts, playback settings, sources, progress, personal collections, saved searches, row arrangements and unrelated add-ons. Fresh and Standard reinstall remain separate workflows.

Validated with 949 installer/release tests, 1,252 controller tests, clean/Standard and in-place package combinations, independent review, reproducible builds and isolated native Kodi updates. General platform validation used a platform shim on macOS; this release was not playback-tested on a physical Fire Stick or Apple TV during publication. Personal Fight Zone and account data are excluded.

Kodi 21.3 Omega. General supports Fire TV/Android; Apple TV & Mac retains its platform-specific adjustments and requires a compatible Kodi application. Native platform binaries remain Kodi-managed.

## Acceptance and recovery

Both full packages and the two public-1.1.40 component packages reproduce byte-for-byte. Each edition has 709 verified release-file hashes. The independent review has no unresolved findings. Clean/Standard coverage includes 20 baseline/edition/mode combinations; in-place/component coverage includes 10 combinations. No real user credentials or device userdata were accessed by the isolated native checks. Native tests used synthetic accounts, denied network and personal Kodi profile access, and asserted windowed mode.

The native General test first settles the original add-on first-run initialization before creating custom preferences and synthetic sign-ins. Initial test failures were traced to fixture prerequisites, first-run settings serialization and explicit window flags; production payload bytes were unchanged by these test corrections. Existing saved values, including custom Umbrella colors and synthetic Simkl login, then passed preservation.

Previous immutable releases remain available. The installer validates the complete supported Helper/provider set before mutation and retains interrupted-update recovery. Use the installer update transaction rather than extracting ZIP contents into a personal profile. A manually forced different add-on version is outside normal protected updates.
