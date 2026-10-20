# Tested autoplay release implementation plan

> For agentic workers: execute inline using superpowers:executing-plans, with a whole-branch review at the end.

**Goal:** Publish the tested Mac Options and same-show source-selection changes in both Build 1.1.15 editions and Installer 1.0.20.
**Architecture:** Keep the reproducible clean-baseline builder, OpenWizard preservation flow, managed-addon protection, platform-specific files and shared reliability/privacy repairs. Promote exact tested code, changing only controller version metadata to 0.1.84.
**Tech Stack:** Kodi 21.3, Python, SQLite, deterministic ZIP archives, GitHub Releases/Pages.
**Spec:** User approval on 2026-10-20 and local natural-season-mac-2026-10-20/verification.json; final tested source commit 0b674a3.

## Global constraints

- Do not contact or update Fire Stick or Apple TV; defer their device acceptance until home.
- Preserve settings/accounts via the existing Standard path; no live-profile payload capture or product behavior redesign.
- Keep prior version manifests, receipts, release assets and recovery copies intact.
- Do not infer three-device acceptance for these new changes from historical receipts.

## Review focus

- Upgrade from existing released Umbrella trees and current Mac trial; reject mixed/foreign trees before cleanup.
- Old Installer19 rejects the new policy before device setup or cleanup.
- Standard install preserves accounts, playback preferences, rows and native components.
- Both clean builds contain exact tested source; edition differences and userdata defaults stay unchanged.
- Native evidence matches code and has explicit Mac-only limits; no private values enter public artifacts.

### Task 1: Managed upgrade integration

Files: managed_addons.py, platform_compatibility.py, wizard.py, managed-umbrella.json, tests/test_managed_umbrella.py, tests/test_autoplay_install_flow.py.
- [x] Test full-tree digest acceptance/rejection and new-policy real Standard preservation (RED).
- [x] Add exact complete-tree digest support, new autoplay policy/minimum20 and managed flags (GREEN).
- [x] Preserve all existing source guards and transaction behavior; verify synthetic account-only defaults too.

### Task 2: Exact release packaging

Files: tools/build_release.py, tools/verify_release.py, controller manifest84, controller/installer addon.xml, release contract tests, source-bound native receipt, CI.
- [x] Promote three tested Umbrella modules and exact controller source with version metadata only changed.
- [x] Require source-bound Mac natural run plus existing historical gates; never rewrite historical evidence.
- [x] Run installer/controller/policy/progress/probe suites and deterministic rebuilds of both editions.
- [x] Compare new packages against public1.1.14; only expected code/installer/marker/README may differ. Userdata and platform files otherwise exact.

### Task 3: Release and public readback

Files: hosted catalogs/setup15, addons.xml/md5, wrapped Installer20, release validation and project-status docs.
- [x] Review entire branch and complete final syntax, privacy, CRC, dependency, managed manifest and preservation checks.
- [x] Publish exact reviewed source/assets with CI green, then activate catalog/Pages.
- [ ] Verify anonymous asset bytes, metadata MD5, catalogs, installer ZIP and repository links.
- [ ] Report release versions, preserved state, test coverage and deferred Fire/Apple device updates.

## Ledger

Ruling: User has explicitly authorized publishing both builds/installer; no repeat integration menu is required. Existing isolated task checkout is reused on release/1.1.15; no other workspace or device is changed.

Task 1 complete: real Standard and account-only preservation plus exact-tree preflight tests. RED established unsupported-policy refusal and mixed-tree acceptance under old logic; new full-tree pins and policy support pass the targeted contracts.
Ruling: retain historical release gate ordering before adding the exact-source Mac gate, so historical failure contracts remain intact. Current progress contracts use the maintained zero-resume suite rather than the superseded rejected zero-percent pause contract. No playback implementation was changed during packaging.

Task 2 complete: 572/671/36/16 checks pass, including 87 current progress contracts. Full verifier, reproducibility, 14-path public-baseline comparison and private-value egress checks pass. Independent review passed30 focused tests with no blockers. Task3 pending CI/publication/public readback; device deployment remains excluded.

Task3 publication checkpoint: source47c8d89 candidate/tag CI39514383332/39514717161 pass. Release v1.1.15 is public and all three anonymous downloads match frozen SHA256/size/CRC. Reviewed main/Pages catalog activation and exact public byte readback are the final distribution step; device updates remain excluded.
