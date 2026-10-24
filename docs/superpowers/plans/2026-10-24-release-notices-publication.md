# BlackLanturn release notices and row performance Implementation Plan

> For agentic workers: execute inline with superpowers:executing-plans; user explicitly approved implementation and publication.

**Goal:** ship curated versioned notices in both builds/Installer and repair verified row slowness without losing user state.
**Architecture:** promote Mac-tested release engine/UI; add Installer preservation and published catalog/receipt integration to OpenWizard. Diagnose Fire Stick first; apply only measured fixes.
**Tech Stack:** Kodi21.3 Python/XML, current build pipeline and GitHub hosting.
**Spec:** ../specs/2026-10-24-release-notices-publication.md

## Global Constraints
Preserve settings, authorizations, source choices, artwork, watch/progress. No Apple TV access. Fire Stick available for diagnostics/necessary repair, other device rollout deferred. Keep platform workarounds and immutable historical receipts. No external network/VPN configuration changes.

## Review Focus
Interrupted/partial install must not report completion. Standard update must retain disabled notices and history; clean must not copy accounts or test state. Cache failures/offline must not block rows or falsely succeed. Catalog versions/important wording must match actual published payload. Slow rows must retain metadata/focus and never cache empty transient failures.

### Task 1: Diagnose Fire Stick row delay
- [x] Snapshot source/settings/database/auth; gather read-only source, logs, network timing and native row baseline.
- [x] Identify bottleneck; write minimal regression reproducer and run RED before any repair. Implement smallest fix and GREEN; record before/after native measurements and preservation.

### Task 2: Integrate tested notices
- [x] Promote overlay into canonical controller with new manifest. Add regression tests for install-proof completion, published version copy, no generic inventory and state preservation RED→GREEN.
- [x] Update Installer preserve/default/clean behavior and fixed notes route, remove generic inventory completion sampling, advance exact manifests and release packaging.
- [x] Build both edition payloads; generate curated release catalog from the exact packaged files. Native full suite and package suite pass.

### Task 3: Validate clean and Standard
- [x] Test actual Installer installation core with both editions in disposable network-blocked Kodi profiles; verify clean defaults/quiet baseline and Standard accounts/settings/history/notice preference.
- [x] Recheck native available/completed notes and Installer handoff; compare preservation baseline. Record exact artifacts/hashes, historical acceptance separately from new native coverage.

### Task 4: Review and publish
- [x] One independent whole-change review, fix important findings RED→GREEN and green suite.
- [ ] Commit/push tested sources, verify CI, publish exact artifacts through existing pipeline, verify anonymous hashes, activate build/Installer/catalog pointers.
- [ ] Final Fire/Mac preservation and public readback, remove owned staging/launchers; leave Apple TV untouched. Record final versions, performance and limitations.
