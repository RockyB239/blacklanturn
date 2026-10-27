# Low-memory Updates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement task-by-task.

**Goal:** Lower update RAM use, preserve interruption recovery, and diagnose the Fire Stick row-speed report before publishing both build editions and Installer.
**Architecture:** Existing OpenWizard/journal/portable-lock architecture; bounded stream helpers and temporary updater activity lease. Existing UI and patch policies stay intact.
**Tech Stack:** Kodi21.3, Python stdlib, native FireOS/ADB and Kodi APIs.
**Spec:** docs/superpowers/specs/2026-10-27-low-memory-updates-design.md

## Global Constraints

No preferences/account reset or sources/ edits. Preserve unrelated addons, private Fight Zone, explicit icon choice and platform-specific components. No VPN/network changes. Do not publish until actual Fire memory and controlled interruption recovery pass. Reuse the existing isolated checkout at source1f318d4.

## Review Focus

- Large/compressed files must not allocate whole content; all validation must remain enforced.
- Late retained-source drift must fail before reconstruction and also be checked while streaming.
- Cancellation, abort and exceptions release leases/locks and cannot create success receipts.
- Interrupted Installer+Controller replacement must cold-recover exact prior code and preserve every saved setting/account.
- Normal browsing must not gain network work, polling overhead that changes measured row speed, or stale results.

### Task 1: Record baseline and preservation proof
**Files:** work/update-memory-2026-10-27/device-work/; existing benchmark.py/row_readiness.py; private recovery records.
**Interfaces:** produces verified recovery, benchmark-before.json and equivalent old-updater memory baseline.
- [ ] Capture/fetch fresh Fire recovery; native health and installed-source fingerprints.
- [ ] Run identical4-cycle matched row protocol and compare historical valid130 receipts; inspect current logs before proposing a row fix.
- [ ] Measure old updater staging on an isolated Fire scratch profile without applying it or touching live saved data.

### Task 2: Bound update memory
**Files:** resources/libs/stream_io.py(new), component_update.py, inplace_update.py, tests/test_streaming_update.py(new).
**Interfaces:** stream hash/copy helpers; preserve existing component schema, expand/prepare/apply/recover interfaces.
- [ ] Add failing large-file/early-fallback/CRC/drift/preservation tests and observe failures.
- [ ] Stream retained trees and incoming ZIP files into reconstructed output; preserve exact hash document semantics and reject drift before reconstruction.
- [ ] Stream addon staging/hash reads; retain atomic write/fsync/journal/rollback semantics.
- [ ] Run focused and full Installer tests; compare isolated staging output bytes and peak memory.

### Task 3: Pause competing work during updates
**Files:** Installer resources/libs/update_activity.py(new), wizard.py; Controller update_activity.py(new), provider_work.py, live_review.py; corresponding behavior tests.
**Interfaces:** ephemeral shared update lease with ownership, expiry and finally cleanup; no preference writes.
- [ ] Add failing lease cleanup/expiry, queued-row deferral and preview deferral tests.
- [ ] Hold lease only after accepted update; keep progress UI active with keep-Kodi-open wording; release on failure/cancel/success.
- [ ] Defer new background row work and automatic previews while lease is active; preserve pending work and resume afterwards.
- [ ] Run Controller/Installer suites and same matched navigation benchmark, fixing only demonstrated regressions.

### Task 4: Actual Fire acceptance
**Files:** owned native memory/recovery scripts and private receipts.
- [ ] Compare old/new update preparation with same payload and scratch profile, native RSS sampling, and source/output parity.
- [ ] Exercise clean/Standard/inplace/component cases in isolated Kodi before live mutation.
- [ ] Perform controlled process interruption at journaled addon replacement on Fire; cold-launch recovery; verify original source/settings/auth/progress, then retry successfully.
- [ ] Re-run row speed, verify accounts/native preferences and remove temporary staging.

### Task 5: Package and publish
**Files:** latest build/verifier, manifests, Installer/version metadata, public notes/catalog and validation records.
- [ ] Produce new immutable full/component editions and Installer; retain icons and private-data boundary.
- [ ] Run full suites, exact rebuild, privacy, native install cases and independent code review.
- [ ] Publish accepted assets only after CI; anonymously verify, activate catalog, verify final CI/Pages.
- [ ] Verify final Fire installed/public identity and preservation; update current-state/results/ledger. Other live devices require no change for this task.
