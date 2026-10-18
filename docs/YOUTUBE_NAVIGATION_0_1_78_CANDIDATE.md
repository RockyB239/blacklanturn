# YouTube navigation and captions 0.1.78

Development candidate; Fire Stick and Mac validated. Apple TV rollout/public distribution withheld after native acceptance crashes. Exact source: `controller-source/manifest78.json`. Receipt: `controller-source/youtube-navigation-verification.json`.

The TV devices had not received the Mac-only 0.1.77 continuation candidate. This version includes that common continuation/refresh pipeline, with these further corrections:

- Never re-apply category diversity filtering to existing cards at a terminal page or cache-evicted return. Filter incoming continuation batches only, preserving existing artwork, watch metadata, order and selected identity.
- Next below the memory cap enters the first appended choice rather than following the synthetic Next tile to its new trailing position. Previous insertion, terminal completion and empty capped terminal responses retain valid selection.
- YouTube title fields allow two complete lines (56px), with a separate 32px channel/duration field. Native row height360 is preserved through tabs, discovery, details return and browse restoration. Other sections keep their existing heights.

Fire Stick and Mac each passed all17 native signed-in Home rows, finite row-end navigation, bounded Next fallback, eviction/revisit, caption discovery/return, bottom refresh access, exact-video windowed preview and external navigation cancellation. Normal restarts matched all309 source files. Protected settings and authorization grants were preserved (Fire13 files; Mac27).

Tests:597 controller,193 installer/release,16 device-validation. Terminal/category eviction, Next selection and caption transition cases were observed failing before repairs and passing after. Independent review accepted the final source.

Apple TV failed native continuation acceptance. Dispatched GUI snapshots did not eliminate its exit, so the native fault remains unresolved. Original direct-reader diagnostic runs are inconclusive and are not acceptance. A custom code-location trace confirmed a native segmentation fault but did not provide a useful Python frame. Approval review rejected raw application-log and OS crash-report exports; only safe receipts, filenames and generated code-location diagnostics were retrieved. Explicit permission for a private OS crash report is pending. Restore only the prior controller0.1.75; never replace current user settings or authorization grants with stale snapshots.

The release builder remains intentionally pinned to validated manifest76/build1.1.9/Installer1.0.15. Do not promote this candidate or weaken the release gate until Apple investigation and deliberate release validation are complete. The wrapped candidate contains source only, no profile/account data; SHA256 `c88f2cbe9cd4904a353680b88ef1129236deb9d13b3e2236b68565a2e8c339b6`.
