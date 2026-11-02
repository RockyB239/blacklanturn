# Reliability and polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete the six user-approved reliability and polish items without changing recommendations or personal preferences.

**Architecture:** Keep existing Kodi21.3 controller/OpenWizard architecture. Correct only diagnosed boundaries, use existing caches and generation ownership, and add host-side release checks rather than resident diagnostics.

**Tech Stack:** Python3, Kodi21.3 native interfaces, existing XML/PNG artwork and unittest.

**Spec:** docs/superpowers/specs/2026-11-02-reliability-polish.md

## Global Constraints
- Preserve settings, authorizations, recommendation behavior, playback routing and private Fight Zone.
- Keep Mac windowed; use idle devices only.
- Sources/ references and accepted releases are immutable.
- No public publication or new resident monitoring in this task.

## Review Focus
- Shutdown while provider calls are slow: retire queued work and stop existing loops without changing audio preferences.
- A late result after Back or new navigation must not replace current cards or focus.
- Missing artwork cannot qualify as a fast successful load.
- Long fallback messages and remote-only selection must fit without hiding playback choices.
- Native preference persistence and account/session renewal must remain distinct.

### Task 1: Qualify and repair shutdown lifecycle
**Files:** controller-source/addon/default.py, live_review.py, provider_work.py; tests under controller-source/tests as evidence requires.
**Interfaces:** Existing window lifetime, alive flag and Kodi Monitor.abortRequested; preserve their external contracts.
- [ ] Preserve baseline source/preferences and collect bounded exit thread stacks on Mac first, then Fire if necessary.
- [ ] Write a behavior test for the confirmed wait; observe it fail on accepted57.
- [ ] Apply the smallest cancellation/cleanup correction.
- [ ] Run relevant tests and the controller suite, then repeat native shutdown checks with no preference changes.

### Task 2: Enforce visible performance and visual release checks
**Files:** tools/device_validation/performance_gate.py, native_benchmark.py, tests under tools/device_validation.
**Interfaces:** Existing compare(before,after) receipts; extend validation without treating first visits as cold.
- [ ] Capture baseline native cached page/scroll/artwork/remote timing and source identity.
- [ ] Add failing cases for missing artwork, protocol mismatch, deep-row regressions and invalid visual geometry.
- [ ] Extend existing host-side acceptance checks with compatible explicit evidence fields.
- [ ] Verify adverse cases fail and valid receipts pass; inspect native Mac layouts in both icon styles without persisting preference changes.

### Task 3: Slow-network and navigation continuity
**Files:** controller-source/addon/live_review.py, provider_work.py, row_results.py or existing cache owner identified by trace; related behavioral tests.
**Interfaces:** Existing generation/path ownership and cached row selection.
- [ ] Exercise timeout, stale response, rapid Back and page-end cases against real controller methods.
- [ ] For any failure, pin it with a failing test before code changes.
- [ ] Retain cards/focus and retire obsolete work using existing bounds; do not add provider calls.
- [ ] Compare native before/after browsing and source/account preservation.

### Task 4: Explain playback fallbacks
**Files:** Current packaged Umbrella autoplay-size module identified by build_release157 recipe; lifecycle tests.
**Interfaces:** Existing source-session constraints and fallback outcome; no extra scraping or dialogs.
- [ ] Trace current selection/fallback reasons and existing notification boundary.
- [ ] Add failing behavior tests for no suitable size, provider failure and manual selection.
- [ ] Show brief reason-specific text only when a source-selection fallback occurs.
- [ ] Verify normal autoplay remains quiet and selection/provider behavior is unchanged.

### Task 5: Integrate and verify the personal candidate
**Files:** New candidate manifest and validation evidence; no hosted metadata.
- [ ] Run controller, affected compatibility and release-check suites.
- [ ] Test Mac windowed, preservation and artwork; qualify Fire shutdown and only apply tested personal changes when idle.
- [ ] Independently review the whole diff, fix important findings with regressions, retain rollback and report remaining limitations.
