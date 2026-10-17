# Release 1.1.7 acceptance

Installer 1.0.13 and both clean build editions now share an explicit, noncredential playback/Trakt policy. Kodi audio follows its interface language (locale.audiolanguage=default), with forced-only subtitles. Helper enables watched indicators and Trakt incoming watched/resume sources plus scrobbling. Umbrella uses actual current indicators.alt=1/scrobble.source=1 selectors and matching Trakt labels. The obsolete trakt.scrobble field is not relied on.

Standard updates capture only the ten approved preferences before cleanup, preserve stored choices including Kodi default=true values, and restore them after account restoration. Missing fields receive build defaults. Deliberate different language/provider/disabled choices remain preserved. Account-only clean resets these preferences while preserving selected known authorizations. Retry snapshots retain the original choices and install mode; preference restoration completes before the account snapshot is committed. Tokens and device data are excluded from publication.

Schema-3 payloads require Installer 1.0.13. The old Installer 1.0.12 fixture rejects them before setup/cleanup. Package and native preflight gates verify all ten explicit values and their actual addon settings definitions. CI rebuilds both editions from immutable clean 1.1.2 baselines. Controller 0.1.74 (303 files) and reviewed managed Helper (471 files) are unchanged. Existing per-addon Helper update protection remains.

## Validation

- 189 installer/release unit and integration checks passed; 523 unchanged controller checks and ten maintained native-probe checks passed.
- Actual OpenWizard preflight, cleanup, extraction, restore, registration and finish passed in a disposable native macOS Kodi21.3 profile for standard updates both without and with Keep GUI, and account-only clean mode. Stored English survived both update paths; clean defaults and selected account data survived clean installation. All 80 native component files remained identical, the addon registry passed integrity_check and Helper remained protected from automatic replacement.
- Apple TV native probes confirmed XML exists in Kodi VFS while no physical XML exists; a physical shadow can be ignored. The Installer now reads/writes XML through the authoritative native store. Exact native readback, shadow precedence, approved preference capture and temporary native cleanup passed. Final real GUI/Helper/Umbrella XML bytes remained unchanged during the owned cleanup probe. No real Apple TV wipe was performed.
- Native tvOS cleanup inventories XML before deleting physical directories and respects the existing preserve/exclude rules. Installed-addon settings.xml is checked even when its cache directory was evicted. Orphaned native XML beneath wholly evicted directories, especially auxiliary files or uninstalled addons, may remain; this is not an exhaustive erasure of the tvOS preferences store.
- Independent source review found no remaining blocker for the named playback/account preservation contract. It identified the native-store and cleanup gaps, which received focused regression/native checks.
- Both exact packages pass CRC, complete manifests, clean defaults, schema/version, installer parity, managed Helper and unchanged controller checks. Public publication inputs are scanned against private authorization recovery data before release.


## Package hashes

| Edition | SHA256 |
| --- | --- |
| General | ea12ebff109c77a12a12df91ae7ff68ece6199cda9aa2f39a11444db4d5c4198 |
| Apple-TV-Mac | 6ce6ae696930749c445fa751ce048064fdea215e5aa73d73deba891946e5be78 |

## Limits and recovery

The clean distribution contains no personal authorizations; new users must authorize their own accounts. Forced-only subtitles require correctly flagged tracks. Following system language means Kodi's interface language, not independent operating-system detection. Outbound scrobbling and every cloud title are not newly certified by these installer tests. A full personal-device clean installation, wider Android hardware, Intel Mac and exhaustive tvOS native-store erasure remain untested. Previous immutable releases, private recovery copies and pending account snapshots remain available. Update the Installer before selecting build1.1.7.
