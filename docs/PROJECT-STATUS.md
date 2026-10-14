# BlackLanturn distribution — 1.1.0

Kodi 21.3 Omega remains the target. BlackLanturn Repository and the OpenWizard-based BlackLanturn Installer retain their existing identities.

## Hosting and editions

GitHub Pages hosts repository metadata, Installer 1.0.8, setup guidance and the new catalog at `hosted-files/builds-v2.txt`. GitHub Release `v1.1.0` hosts exactly two clean payload assets:

- General: Fire TV/Android, derived from the existing Fire Stick edition, with its tested YouTube fix and lower-memory defaults.
- Apple TV & Mac: Mac baseline shared skin/controller, with platform-native components retained. Apple TV quality was not reduced.

The old `hosted-files/builds.txt` remains upgrade metadata for older installers. Its old edition names and versions are retained, but payload links are retired. Update the installer to 1.0.8 before using the new packages. Never put the new payload URLs in the legacy catalog: older installers lack native-component preservation.

## Install safeguard

Validate ZIP integrity and platform before cleanup. Keep compatible device-native playback components and their preferences. Missing components use Kodi's official repository with the official-only repository policy. Cancellation, failed setup, an incompatible component or wrong platform stops before cleanup. After extraction, register installed addons in the device's existing database. Payloads contain no native binaries, device addon registry or personal credentials.

## Validation

18 installer safeguard tests passed, plus independent source/catalog review. A disposable account-free Mac profile passed actual OpenWizard wipe/extraction, existing native-file preservation, addon registration, native cold start and movie browsing. Personal Mac and Apple TV passed targeted updates. Apple TV playback included 3840×2160 HEVC with English EAC3 5.1. Preview handoff, episode-to-play, cast/audio visibility, season posters, three Umbrella player choices and image-first Next Up were checked on Apple TV.

Full clean ZIP installation on the personal Apple TV or Fire Stick was not performed. Broader Android/Intel Mac hardware and credit-marker timing at a real episode ending remain untested. Fire Stick testing was not interrupted. Setup and recovery guidance: `hosted-files/setup-1.1.0.txt` and each payload's `userdata/BlackLanturn-README.txt`.

## Recovery

Previous clean editions are archived locally before cloud retirement. Private device recovery/preferences remain access-restricted and excluded from publication. Repository rollback is available through Git history; restore old payload links only when their corresponding verified downloads are available again.
