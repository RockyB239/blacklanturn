# Apple TV settings reset: diagnostic directory-cache trigger

On October 17, 2026, an earlier native diagnostic listed the actual Kodi userdata and Umbrella profile directories through xbmcvfs.listdir without trailing slashes. That diagnostic reported the virtual settings XML absent from the listing. Umbrella's persisted settings subsequently contained addon defaults, including empty authorizations and disabled external provider configuration. The user confirmed no intentional reset. The verified private profile was restored; all 21persisted userdata entries matched, and the same Trakt account returned HTTP 200 after restart.

## Reproduced mechanism

Kodi 21.3 tvOS keeps userdata XML in NSUserDefaults while directories and ordinary files remain on disk. Its native directory implementation adds virtual XML only when the requested path exactly matches the XML file's parent directory, including the trailing slash. A slashless directory request can return a successful listing that omits virtual XML. Kodi caches that listing. File.Open and cached File.Exists then consult it and can report the XML missing before consulting native storage. The Python xbmcvfs.exists wrapper bypasses the file cache, so it can still return true while File.readBytes returns zero bytes.

A fresh Apple TV test reproduced this in a unique owned directory containing only fake settings:

- Initial native XML read returned the exact fake content.
- Slashless directory listing omitted settings.xml; exists stayed true, but the subsequent read returned zero bytes.
- Listing the same directory with its trailing slash restored the XML read immediately, without rewriting it.
- All three real GUI/Helper/Umbrella XML files remained byte-identical.

Kodi's CAddon.LoadUserSettings treats a cached nonexistent user XML as a profile with no saved values. A later SaveSettings serializes the initialized defaults over the userdata XML. Umbrella's startup code can save selector display labels, providing a reachable write after default loading. This explains the observed full-reset shape. The original overwrite call was not captured in the rotated log; the cache failure is reproduced natively, and the final overwrite link is supported by source tracing rather than a destructive test against real accounts.

References: [Kodi 21.3 TVOSDirectory](https://github.com/xbmc/xbmc/blob/21.3-Omega/xbmc/platform/darwin/tvos/filesystem/TVOSDirectory.cpp), [NSUserDefaults directory matching](https://github.com/xbmc/xbmc/blob/21.3-Omega/xbmc/platform/darwin/tvos/TVOSNSUserDefaults.mm), [file cache checks](https://github.com/xbmc/xbmc/blob/21.3-Omega/xbmc/filesystem/File.cpp), [Python exists bypass](https://github.com/xbmc/xbmc/blob/21.3-Omega/xbmc/interfaces/legacy/ModuleXbmcvfs.cpp), and [addon user-settings load/save](https://github.com/xbmc/xbmc/blob/21.3-Omega/xbmc/addons/Addon.cpp).

## Correction and acceptance

Maintained native diagnostics now have a common slash-normalized directory reader and a validated XML reader that primes the correct directory before reading. An unreadable file stops the diagnostic; no default file is written. The owned-only native regression and its checks work under optimized Python, which disables assert statements. The earlier one-off diagnostic's real-profile listings were corrected; future storage diagnostics use the maintained guard.

Native acceptance with the maintained guard reproduced the cache failure only in fake XML, recovered the exact fake content through guarded reads, removed the owned probe, and kept all real XML bytes unchanged. After restart, an independent host comparison retained all 21persisted userdata entries semantically, excluding only peripheral last_active telemetry. Trakt users/settings returned 200 for the same account. No real playback settings, authorizations, history or addon registry were changed.

Six new regressions passed, alongside the ten existing native-probe checks and 189 installer checks. Both existing 1.1.7 packages still pass exact installer/controller/managed-Helper and clean-default verification. Independent review found no blocking issue and confirmed the distinction between reproduced cache behavior and the inferred original overwrite.

The current Installer 1.0.13 native XML inventory already uses trailing slashes; the controller has no xbmcvfs.listdir calls. The audited Umbrella listings concern icons, skin packs, downloads and library folders rather than the account-settings directory. This correction changes diagnostic tooling and documentation, not runtime addons, playback defaults or build payloads. Build 1.1.7 and its private recovery copies remain intact.

The underlying Kodi 21.3 bug remains. This prevention covers the maintained diagnostic path, not arbitrary unrelated callers. No unconditional automatic restoration, credential-sharing mechanism, addon upgrade or authentication reset was added.
