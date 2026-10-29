# Row customization and series status implementation plan

Use superpowers:executing-plans inline; one fresh review at end. User explicitly authorized implementation and Mac then Apple deployment.

Goal: provide per-section move/pin/hide/reset controls and reliable series labels without slower browsing.
Architecture: small row_layout store plus native UI mixin; apply overlay at section entry and reconcile dynamic YouTube shelves. series_status reads existing public metadata only in worker work and displays via title_presentation.
Spec: ../specs/2026-10-28-row-customization.md
Constraints: Kodi21.3; no Fire Stick access, no publication, preserve existing two-file preview fix, preferences and accounts. Existing source editor remains available. No per-title network work.
Review focus: all-hidden/one-row states; duplicate paths/new categories; YouTube first-two assumptions and refresh focus; corrupted storage/disk failure; unknown/stale status; saved layout survives restart.

- [x] Baseline: back up exact Mac source/saved files and preferences; matched cached section/deep browsing timings.
- [x] Tests RED then GREEN: layout persistence, section isolation, pins/order/hidden/reset, dynamic rows, last-row protection, atomic failure and corrupt reads; native menu routing.
- [x] Tests RED then GREEN: status values/types/missing data, bounded readonly cache and no network; presentation keeps watch state separate.
- [x] Integrate existing settings/Options and YouTube catalog-refresh paths; full Controller suite.
- [x] One fresh review and fix important issues with RED/GREEN coverage, complete suite.
- [x] Install exact Mac candidate, native customization/reset/restart/pagination/status checks and matched speed comparison; protected-state comparison.
- [x] Apple baseline, install same candidate, repeat native behavior and matched speed/preservation checks. Leave Home idle; stage source and results only.

Completed evidence: /Users/ChrisFaulkner/.codex/.chatgpt-projects/g-p-6a0726c39718819199402b5f239428f9/work/row-customization-2026-10-28/RESULTS.md; one review, one covered fix pass, 1007tests and101native checks. No commit/push/publication was performed; existing unrelated staged trial remains preserved.
