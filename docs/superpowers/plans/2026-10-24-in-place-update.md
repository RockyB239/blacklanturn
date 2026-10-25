# BlackLanturn In-place Update Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline. User explicitly approved implementation and testing before publication; no further design questions are needed.

**Goal:** Existing users choose Update BlackLanturn in Installer to receive bundled add-on code and patches together without reinstalling their setup.

**Architecture:** A separate Installer transaction validates the downloaded edition, complete managed source, dependency closure and target paths; stages whole bundled code trees; replaces only those trees; rolls back partial work on failure. No wipe, extraction of userdata defaults, account restore or settings migration. Existing Fresh/Standard install behavior remains separate. The running Installer updates through its repository.

**Tech Stack:** Existing OpenWizard Installer, Python 3, Kodi 21.3 APIs, ZIP payloads.

**Spec:** Direct user instruction in this conversation, 2026-10-24.

## Global Constraints
- No Fire Stick connection or personal-device changes.
- All saved data, accounts, playback, sources, database history and unrelated add-ons remain in place.
- Only marker/catalog/completion metadata and Installer update bookkeeping may change in userdata.
- Bundled managed add-ons use complete reviewed source, native components stay Kodi-owned, newer compatible ordinary dependencies stay whole.
- No silent downgrade, cross-edition update, playback interruption or full-install fallback.
- Failed/interrupted updates retain recovery and cannot claim completion.

## Review Focus
- Failure between old-directory rename and replacement, including process interruption: recover complete prior trees.
- Existing user add-on dependency on bundled shared code: validate final declared dependency closure without editing unrelated code.
- Concurrent updater or linked target path: refuse before any replacement.
- Saved settings/schema/history files: never extract or restore them, including unknown custom files and databases.
- Current/newer ordinary add-on and running Installer: retain whole compatible tree and avoid self replacement.

### Task 1: Transaction and preservation
**Files:** resources/libs/inplace_update.py; tests/test_inplace_update.py
**Interfaces:** prepare(archive, home, kodi); apply(plan); recover(home). Production preflight delegates exact managed checks to existing compatibility validators.
- [x] Write/run failing transaction tests with older add-ons, custom saved data, unrelated add-ons, failure and interruption injection.
- [x] Implement staging, final dependency closure, exact readback, journal rollback, lock and version/edition checks.
- [x] Run focused tests and commit.

### Task 2: Installer entry points
**Files:** wizard.py; common/router.py; gui/build_menu.py; gui/window.py; platform_compatibility.py; tests/test_inplace_update_ui.py
**Interfaces:** Wizard.update(name) consumes transaction without install.wipe/extract/accounts; router and update notice lead there.
- [x] Write/run failing routing/flow tests.
- [x] Add explicit Update BlackLanturn with preservation summary, no Save Data dependency or full-install fallback, restart prompt.
- [x] Run focused and existing Installer tests; commit.

### Task 3: Exact candidate acceptance and publication
**Files:** tools/build_release.py; release notes; docs/MANAGED-ADDON-UPDATES.md; release124 evidence outside source.
- [x] Build both candidates and Installer, test exact-artifact in-place updates including older/current/newer dependency cases and untouched-data byte comparisons.
- [x] Run isolated native Mac Kodi tests; retain separate clean/Standard regression acceptance and native limits.
- [x] Review once, fix findings with regressions, run full suites and privacy checks before publishing.
- [ ] Publish accepted immutable artifacts and verify public hashes/catalog. Fire Stick remains untouched.
