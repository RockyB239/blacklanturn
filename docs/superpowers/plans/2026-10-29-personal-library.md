# Personal library Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline. Steps use checkbox syntax.

**Goal:** Implement the four approved browsing/end-of-series features on the Mac only.
**Architecture:** Pure bounded library operations over the preserved controller object, a small UI mixin, provider-owned release-order browser, and a cancellable series-end session tied to actual playback identity. Existing row and watched pipelines stay in charge.
**Tech Stack:** Python3, Kodi21.3 WindowXML, unittest, existing TMDbHelper routes/cache.
**Spec:** docs/superpowers/specs/2026-10-29-personal-library-design.md

## Global Constraints
- Mac trial only; no other devices/public versions/assets changed.
- Preserve all existing settings, authorizations, saved data and private Fight Zone.
- No new service, dependency, idle polling or synchronous metadata while browsing.
- No different-series autoplay; next episode always wins; failure is not end-of-series.

## Review Focus
- Duplicate/retyped collection and search identities; cancelling must not persist edits.
- Invalid/malformed preferences; preserve original and refuse destructive overwrite.
- Future or missing release dates, watched/resume state and poster-only fallback.
- Chained episode identity, stop/error/preview and asynchronous ownership races.
- Ordinary browsing timing and all existing settings/account data preservation.

### Task 1: Bounded library storage and UI
Files: create addon/personal_library.py and library_ui.py; modify live_review.py, row_layout_ui.py; tests/test_personal_library.py and test_library_ui.py.
Interfaces: pure functions create/rename/delete/move collections, membership, save/delete/rename searches, build My Stuff rows. LibraryActions mixin consumes self.config/save/open_search/open_discovery.
- [ ] Add behavior tests for duplicate membership, independent collections, deletion/history isolation, limits, invalid input and persisted round trip; observe RED.
- [ ] Implement pure copy-on-write operations and bounded validation in personal_library.py, UI mixin using existing dialogs; observe GREEN.
- [ ] Integrate My Stuff shelves and Search access; test actual methods with native boundary doubles and controller suite.

### Task 2: Movie-series release order
Files: create addon/movie_series.py; library_ui.py integration; tests/test_movie_series.py.
Interface: release_order(items,today) returns ordered items and recommended next identity without dropping metadata.
- [ ] Test shuffled/date/unknown/future/duplicate/provider control inputs and resume/watched retention; observe RED.
- [ ] Implement bounded provider collection lookup from existing local Helper DB, explicit-action-only provider requests, one-row discovery UI and next-title notice; GREEN.

### Task 3: End-of-available-series suggestions
Files: create series_end.py, series_end_core.py, resources/skins/Default/1080i/SeriesEnd.xml; modify playback_runtime.py/default.py/backend_core.py; tests/test_series_end.py and native boundary tests.
Interfaces: fresh last-aired DB reader; exact episode match; SeriesEndSession.observe_current/current/prompt/close; dialog returns Details/open/save/disable without autoplay.
- [ ] Test fresh/expired/missing DB, future/same-day metadata, different chain identity, Stop/error/unknown rejection, disabled and ownership/cancellation, dedup/hide filtering; RED.
- [ ] Add one late asynchronous worker per actual episode and no return-time waiting. Reuse existing end-screen layout separately. GREEN.
- [ ] Test entry-point result routing and unchanged YouTube/normal Up Next behavior; complete suite.

### Task 4: Mac rollout and native verification
Files: task evidence in work/personal-library-mac-2026-10-29 outside public repo; existing native test/control tools.
- [ ] Capture current source/settings/auth/progress baseline and same cached speed visits before changing Mac.
- [ ] Run full Controller and relevant installer preservation tests; independent whole-change review and fix important findings.
- [ ] Install exact trial files without changing version/settings; native test create/edit/remove collections, multiple saved queries/category reopen, franchise ordering and series dialog controls.
- [ ] Verify natural EOF/Stop/chain ownership via isolated test video/provider boundary, report live-provider limits; restore synthetic choices only.
- [ ] Repeat timing and saved-data/account/source comparisons; final populated Home/idle. Write RESULTS/completion with honest coverage, unresolved issues and rollback.
