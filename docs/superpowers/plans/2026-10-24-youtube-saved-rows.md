# YouTube saved rows implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement inline, followed by a fresh final review.

**Goal:** Show account-owned YouTube rows sooner without stale watched status or stale recommendations.
**Architecture:** Bounded atomic display cache, read-only current local history overlay, existing progressive refresh/ownership guards.
**Tech Stack:** Kodi21.3 Python, JSON, SQLite, unittest.
**Spec:** ../specs/2026-10-24-youtube-saved-rows-design.md

## Global constraints
Mac and Fire Stick only. Preserve settings/accounts/history; Apple TV and public builds untouched. No tokens/watch state in display snapshots. Five-minute freshness and24-hour maximum age; bounded disk/memory. No new background polling/preloading.

## Review focus
Account change during I/O; malformed/oversize cache; cleared/changed local history; late refresh versus selection; expired snapshot silently renewed. Each receives a behavior test.

### Task1 — establish evidence
- [x] Verify idle/version state, fresh recovery copies, clean baseline805 tests and before native traces.
- [x] Record diagnosis/design and source locations before implementation.

### Task2 — implement bounded storage and current history
Files: controller-source/addon/youtube_saved.py; controller-source/tests/test_youtube_saved.py.
- [x] RED: storage bounds, account/settings identity, age/no renewal, sanitization, corruption; real SQLite fixture current watch updates/deletions and unknown format rejection.
- [x] GREEN: minimal atomic store and read-only safe local-history reader. No credential/watch data on disk.

### Task3 — integrate existing row lifecycle
Files: youtube_browser.py, youtube_rows.py, live_review.py; test_youtube_saved_integration.py.
- [x] RED: saved first rows, no provider on fresh reuse, actual refresh when stale, snapshots on new feeds/categories, owner retirement, focus/artwork/continuation and watch state contracts.
- [x] GREEN: integrate worker reads/writes and existing progressive updates; tests and complete controller suite.

### Task4 — native candidate and preservation
- [x] Review change and package wrapped candidate controller; preserve build receipt/Installer.
- [x] Install authorized candidate on idle Mac/Fire only; exact before/after sources; repeat native protocol and process-reopen test, refresh and navigation checks.
- [x] Capture after settings/coreDB/history evidence, compare with baseline, remove owned hooks/staging/tunnel. Record results/limits and exact installed versions. No publication or Apple access.

## Execution ledger
Baseline: existing linked worktree;805 controller tests passed. Native before protocol completed/valid on both devices. Original entrypoints restored before timing; settings bytes unchanged. Device full-build receipts1.1.19, Controller90, Installer27.

Final ledger: all27 new regressions and832 controller tests pass. Native Mac/Fire before/reopen/fresh-cache runs complete; watch overlays50cards/device, refresh focus and50→100continuation pass. Exact candidate327files installed on both; protected settings/coreDB/history comparisons pass. Preliminary validation issues (native category_label, visitorNone, duration-1) resolved before final acceptance. Candidate publication and full-build installation remain outside this task. Detailed evidence: work/youtube-saved-rows-2026-10-24/RESULTS.md.
