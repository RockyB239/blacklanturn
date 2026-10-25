# Release 1.1.28 update-flow implementation plan

> Execute inline using executing-plans; user explicitly authorized packaging, validation and publication.

**Goal:** Publish the tested direct-update routing and completion-focus fixes in both editions and Installer.
**Architecture:** Existing OpenWizard-based in-place updater, deterministic clean-baseline packaging and repository/catalog activation. No device update or personal preference change.
**Tech Stack:** Kodi 21.3, Python, ZIP/XML/JSON, GitHub release assets and Pages.
**Spec:** User request and work/update-flow-polish-2026-10-25/RESULTS.md.

## Global constraints
- Build1.1.28, Installer1.0.33, Controller0.1.95; repository1.0.6 and skin0.1.39 unchanged.
- Preserve personal settings/authorizations and unrelated add-ons. Keep Fire Stick on27 for user notification test.
- Retain platform workarounds and all immutable historical proofs; only fresh bound receipts establish new acceptance.

## Review focus
- Incoming Installer33 must remain usable through existing32 self update.
- Direct notification must validate local edition and reach true update only.
- Only completion prompt defaults Close Kodi; cancellation remains possible.
- Historical playback/source patches and ordinary-newer retention remain unchanged.
- Feed/repository assets must match accepted package bytes and not leak private data.

User added: Choose genre immediately follows Details in main Movies/Shows Options, excluded inside seasons/episodes.

### Task1: Version and package candidate
- [ ] Update current version contracts, add manifest95 and scoped128 source/native gates; preserve old manifests/receipts.
- [ ] Add new release notes and deterministic package outputs for both editions and Installer.
- [ ] Run source regression and build/artifact checks.

### Task2: Validate exact candidates
- [ ] Exercise clean, Standard and in-place matrices including existing27/32 state and unrelated saved state.
- [ ] Native disposable Kodi21.3 test: clean/Standard/update both editions; real Installer33 self replacement/cold recovery; normal startup notification direct route and completion focus.
- [ ] Rebuild byte-identically, scan privacy, independent final review, run complete release gates and exact-source CI.

### Task3: Publish and read back
- [ ] Publish exact accepted ZIPs and notes, anonymously verify downloads.
- [ ] Activate catalog/release feed/repository Installer33, validate served hashes and Pages completion.
- [ ] Record release URL, versions and notification cadence. Do not install on or acknowledge notices for personal devices.
