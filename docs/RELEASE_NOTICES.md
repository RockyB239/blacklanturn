# BlackLanturn release notices

This flow reports releases authored and published by BlackLanturn. It does not announce ordinary upstream add-on updates, infer whether a compatibility patch is needed, or inspect third-party add-on inventory. Backend review decides which patches ship and whether the release is important.

## Publishing a release

1. Advance the build version and Installer/controller versions where changed. Use a new monotonically increasing build version, or an explicitly greater release revision for a same-version correction. Never replace published ZIPs or reuse a release ID for different bytes.
2. Author `hosted-files/release-notes-<version>.json`: a short title, concise summary, and sectioned bullets. For an important compatibility repair, start the summary with `Important:` and explain the actual repair in the first section. Keep the summary short enough for the tested notification; the build version is prefixed automatically. Routine changes should not be labeled important.
3. Update build_release.py's target marker, exact controller manifest and packaging gates. Its release_entry function derives each edition's release ID, version, revision and required-file hashes from the actual ZIP payload. Do not hand-copy stale file hashes.
4. Run the controller, Installer, preservation and compatibility suites. Build both editions from immutable clean baselines. Test clean and Standard paths using disposable profiles and synthetic accounts, and record native coverage separately from simulated platform identity. Never use a personal Fresh install as a release test.
5. Test the available notice, View changes, Later, fixed Installer handoff, completed notice, Dismiss, saved preference and no-repeat behavior. Incomplete or failed installation must not produce completion. Bind acceptance to the final source hashes and run tools/verify_release.py.
6. Verify reproducible ZIPs and scan private values before committing. Push tested source and require its CI to pass. Publish exactly those three tested build/Installer ZIPs. Verify anonymous downloads against their final SHA-256 hashes before activating catalog pointers.
7. Publish a schema1 `hosted-files/releases-v1.json` catalog containing both generated edition entries (retain bounded prior releases when appropriate). Update addons.xml/checksum, Installer download ZIP/pointer, build catalogs and setup instructions together. Verify hosted readbacks and CI. The current maximum catalog is30 entries/256KiB; remove oldest entries before exceeding it.

## Runtime behavior

The existing background monitor checks the curated feed no more than hourly. The bundled release entry is available offline immediately after installation; a recent empty network cache cannot hide it. Network failure retains known notes and does not block row loading. Notices defer during playback and close after20 seconds; View changes opens the branded release notes, and Update opens the BlackLanturn Installer.

Standard update preserves the notice preference/history together with supported playback choices, selected accounts and Save Data. New clean installations establish a quiet baseline. A completed notice requires the matching build marker, exact critical installed-file hashes and `userdata/blacklanturn-install-complete.json`. The Installer writes that receipt only after extraction, selected account/settings restoration, add-on registration/protection and operational settings finish. A completion notice is not proof that arbitrary personal media playback was tested.

Older installers refuse Build1.1.20 before cleanup. Update Installer to1.0.27 and restart Kodi first. Repository remains1.0.6.
