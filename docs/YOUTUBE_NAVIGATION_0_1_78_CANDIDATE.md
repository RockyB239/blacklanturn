# YouTube navigation and captions 0.1.78

Development candidate validated on Fire Stick, Mac and Apple TV. Exact controller0.1.78 is installed on all three devices. Exact source: `controller-source/manifest78.json`. Receipt: `controller-source/youtube-navigation-verification.json`.

The TV devices had not received the Mac-only 0.1.77 continuation candidate. This version includes that common continuation/refresh pipeline, with these further corrections:

- Never re-apply category diversity filtering to existing cards at a terminal page or cache-evicted return. Filter incoming continuation batches only, preserving existing artwork, watch metadata, order and selected identity.
- Next below the memory cap enters the first appended choice rather than following the synthetic Next tile to its new trailing position. Previous insertion, terminal completion and empty capped terminal responses retain valid selection.
- YouTube title fields allow two complete lines (56px), with a separate 32px channel/duration field. Native row height360 is preserved through tabs, discovery, details return and browse restoration. Other sections keep their existing heights.

Fire Stick and Mac each passed all17 native signed-in Home rows, finite row-end navigation, bounded Next fallback, eviction/revisit, caption discovery/return, bottom refresh access, exact-video windowed preview and external navigation cancellation. Normal restarts matched all309 source files. Protected settings and authorization grants were preserved (Fire13 files; Mac27).

Tests:597 controller,193 installer/release,16 device-validation. Terminal/category eviction, Next selection and caption transition cases were observed failing before repairs and passing after. Independent review accepted the final source.

Apple TV recovery completed after the user approved private OS crash-report inspection. The faulting native stack was Kodi's `Screenshot` builtin, invoked by the diagnostic after the first row's pagination; the progress receipt had not yet advanced, so those failures initially looked like continuation crashes. The test now omits `TakeScreenshot` on tvOS while retaining all17 row, finite-end, cap/Next, eviction/return, caption-height, refresh-access and exact-video preview checks. Independent review confirmed the retained native test logic and exact309-file manifest78 parity. All checks passed. Preview navigation cancellation took1.544s; category batches observed0.342–0.844s. These are single bounded observations, not cold-load guarantees.

Apple normal startup/source audit passed with Home ready. All24 protected files were exact or semantically equivalent (one peripheral activity value changed); all21 persisted preference entries were unchanged. No playback setting or authorization grant was replaced. Apple screenshot-based visual evidence is unavailable because of the native builtin fault; caption geometry was checked through the real native controls. The controller source did not need another change. Private recovery, approved crash data and native receipts remain outside this repository.

The release builder remains intentionally pinned to validated manifest76/build1.1.9/Installer1.0.15. All three-device validation is complete. Deliberate release promotion and distribution checks remain required before changing the published build; retain the existing gate. The wrapped candidate contains source only, no profile/account data; SHA256 `c88f2cbe9cd4904a353680b88ef1129236deb9d13b3e2236b68565a2e8c339b6`.
