# Managed Manual Updates Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline; one final fresh-context review.

**Goal:** Preserve reviewed managed patches through ordinary Kodi bulk updates while allowing ordinary updates.
**Architecture:** Kodi version epochs plus a coupled two-file Umbrella internal-version adapter; immutable historical inventories and independently pinned protected raw inventory. Existing repository/OpenWizard architecture stays intact.
**Tech Stack:** Kodi21.3, Python3, existing ZIP builder/verifier and native disposable Kodi.
**Spec:** docs/superpowers/specs/2026-10-23-managed-manual-updates.md

## Global Constraints
- Preserve settings/accounts/platform variants; Fire Stick untouched.
- No published release, shared-branch push or catalog activation in this scope.
- Never use CoreDevice remove-existing-content=true.
- Only the reviewed Umbrella internal-version accessor/cache adapter may change runtime code; playback and source-selection code remain unchanged. No extra background workers.

## Review Focus
- Wrong/future metadata or mixed code must fail before cleanup.
- Legacy packages remain accepted; old installers refuse protected new packages.
- A deliberate downgrade is distinguishable from ordinary Install all updates.
- All four managed addons and both YouTube platform variants must be covered.
- Standard recovery from exact official97 input preserves saved state.

## Task1: Metadata protection and source verification
- [x] Write tests for exact/idempotent transforms, unknown/wrong XML, no mutation on error, normalized digests and Kodi epoch ordering; run RED.
- [x] Implement resources/libs/managed_versions.py and resources/managed-versions.json; integrate normalized exact hashing in managed_addons.py; run GREEN.
- [x] Add verified clean upstream97 fingerprint/provenance; test known passes and mixed source fails.

## Task2: Candidate packaging and installer floor
- [ ] Write regression tests for policy/minimum enforcement and builder/verifier checks; run RED.
- [x] Integrate metadata after existing code patches in tools/build_release.py; mark Build20/Installer25 and keep historical manifests unchanged.
- [x] Require managed-update policy and exact metadata in platform_compatibility.prepare before cleanup; verify ZIPs/clean+Standard flows and broader regressions.

## Task3: Native tests and recovery/preservation
- [x] Disposable native Kodi positive-control ordinary update plus protected bulk update.
- [x] Mac ordinary candidate installation and Check for updates / Install all updates; exact code/account/preferences checks and browsing/YouTube/source lifecycle tests.
- [ ] Apple restored state/readback verified; perform ordinary update test only with reliable visible UI; do not alter Fire Stick.
- [x] One final branch review, write evidence/limitations and leave publication staged.

Execution ruling: native Mac repair uses ordinary Install from ZIP for all four managed add-ons and Installer25, with exact staged candidate bytes and no userdata payload. This preserves every saved preference/account without running an unnecessary full-build wipe. The Mac build receipt remains1.1.19; Installer25 and managed candidate add-ons are staged locally. This is a real Kodi add-on-install path, not a public catalog delivery test. Apple source/settings/database recovery verified; visible Apple bulk-update acceptance is blocked by DeviceHub AVC stream RTCP timeout.
