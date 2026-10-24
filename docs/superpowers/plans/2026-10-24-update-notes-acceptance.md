# Update notes acceptance — 24 October 2026

Controller 0.1.88 and Installer 1.0.26 installed through ordinary Kodi ZIP installation on Mac and Apple TV. Both exact installed source trees match the reviewed source. Both Build 1.1.20 editions remain unpublished candidates; device feature updates did not perform a full build reinstall. Fire Stick was not contacted.

Passed native checks: quiet initial inventory, an actual Installer version change recorded once, automatic idle Home notice, saved notes route, View changes, Back, Dismiss, preference persistence, no repeated notice after restart. Notice-button interactions replayed the recorded real event without fabricating an inventory change. Mac rendering was visually checked; Apple functional controls were checked through Kodi's native API because its screen viewer fails. Playback deferral/error isolation are automated runtime evidence, not a new full-video native test.

Mac preservation: 3,432 XML values, 120 JSON files, 145 watched file records, four resume bookmarks. Apple preservation: 1,388 saved plist settings, nine JSON files including byte-identical YouTube authorization; existing watched/resume tables were empty and remain so. Three databases on each device pass read-only integrity checks.

Apple remote control and Unknown sources are **user-approved personal settings** kept On and verified saved across normal restarts. Clean-build defaults are unchanged. System-following audio and forced-only subtitles retained. Immutable private before/after evidence is in the project task's work/update-notes-2026-10-24/private directory; credentials must not be published.

Apple's existing Kodi has separate native screenshot, local folder browsing and screen-viewer limitations. First HTTP ZIP attempt failed because the temporary server lacked byte-range handling and Kodi crashed in CAddonInstaller logging; range handling was corrected and both installs succeeded. Temporary source removed and server stopped. Kodi-home staging/tests removed. Two owned non-secret ZIPs (about 12 MB) remain under Documents/BlackLanturn-Update-Notes-20261024 because tvOS denies app access; no unsafe whole-container cleanup attempted.

This feature reports actual installed versions. It does not claim to have rebased and delivered newer upstream add-on code. That work remains separate. Source-bound acceptance receipt: controller-source/update-notes-native-verification.json.
