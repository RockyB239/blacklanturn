# YouTube end-screen release implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this already-authorized publication inline.

**Goal:** Publish Build 1.1.16 in both existing editions so the user can Standard-update the Fire Stick at the hotel.

**Architecture:** Keep the established OpenWizard Installer 1.0.21 and Repository 1.0.6. Rebuild from the same immutable clean 1.1.2 baselines with Controller 0.1.85 and skin 0.1.39; publish versioned GitHub release assets, then activate Pages catalogs only after exact anonymous download verification.

**Tech stack:** Python packaging/tests, Kodi 21.3, OpenWizard, GitHub releases and Pages.

**Spec:** docs/RELEASE_1_1_16_VALIDATION.md plus the approved Mac end-screen behavior and explicit publication request in this chat.

## Global constraints

- No personal-device installation, account reset, VPN change or edits under sources/.
- Preserve platform-specific source, managed compatibility patches and existing Standard preservation semantics.
- User authorizes publication before the first Fire Stick test; describe new native coverage as Mac only and keep historical multi-device evidence separate.
- Keep immutable historical manifests and previous public releases.
- No private accounts/history/native diagnostics in packages or repository.

## Review focus

- Incomplete Home.xml overlay would break fullscreen Back: assert both edition overlays and positive/negative onload guards.
- A stale manifest could certify untested source: bind complete current source to the Mac test snapshot, allowing only version metadata normalization.
- New defaults could replace existing preferences: retain exact Standard rows.json and selected playback/account fixtures.
- Existing autoplay evidence must remain historical: validate against manifest84 and the historical addon metadata, separately from the new 85 receipt.
- Publishing catalogs too early could produce broken downloads: verify uploaded assets anonymously before Pages activation, then verify exact Pages bytes.

## Tasks

- [x] Add failing release tests for current manifest, end-screen native receipt, skin overlay and explicit clean defaults.
- [x] Add immutable manifest85, sanitized native receipt and source-bound verifier; integrate the skin overlay in both deterministic build paths. Keep Installer21 behavior unchanged.
- [x] Pass controller, full installer/release, source lifecycle and native-probe suites; rebuild twice, compare with public1.1.15, verify privacy and preservation fixtures.
- [x] Obtain independent focused review and resolve findings.
- [x] Commit/tag/push release source; require CI success; upload artifacts and verify anonymous hashes/length/CRC.
- [ ] Activate both catalogs/setup notes on main/Pages only after artifact checks; verify exact public catalog/installer bytes.
- [ ] Provide one Fire Stick checkpoint: open Installer Save Data and confirm preservation controls before selecting the release.
