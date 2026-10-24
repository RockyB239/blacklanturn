# BlackLanturn Release Notices Implementation Plan

> For agentic workers: execute inline using superpowers:executing-plans. User approved the corrected behavior and requested implementation.

Goal: notify only curated BlackLanturn releases, accurately before and after installation, on Mac.
Architecture: release_updates.py owns catalog validation, version/revision comparison, bounded state/cache and verified completion. update_notes_ui.py consumes it and fixed Installer handoff; legacy update_notes.py retained for historical Installer recovery compatibility. Separate release-notices.json retains preference and releases, excluding old add-on history. Native UI follows approved mockup.
Tech Stack: existing Kodi21.3 Python, XML, OpenWizard Installer.
Spec: ../specs/2026-10-24-release-notices-mac.md

## Global constraints
Mac only; preserve settings/auth/history; no public publication; no third-party upgrade; no added row requests. Existing build1.1.19 receipt remains unchanged. Test release explicitly isolated.

## Review focus
Invalid/truncated/offline catalog retains cache without false success; wrong edition/version ignored; patch-only revision supported; partial installs never completed; playback/preview/dialog deferral; persistent Later/Dismiss/disable; old inventory never displayed; no executable catalog content; fixed Installer handoff.

### Task1: Release engine
- [x] Write failing tests for semantic numeric versions, revision changes, quiet baseline, unrelated inventory ignored, available/dismiss/restart, disabled, confirmed completion, missing/mismatched proof, malformed/wrong edition feed, cached/offline bounded fetch, legacy preference migration.
- [x] Run new tests RED, implement release_updates.py, run GREEN and existing state tests.

### Task2: Native runtime and layout
- [x] Replace inventory sampling with release sampling; hourly cached background feed plus cheap marker check. View notes/Update/Later and completed View/Dismiss; fixed Installer route; no silent install.
- [x] Use the existing Home1920x1080 layout coordinates; new font hierarchy/sections, approved sizing/placement. Add screen bounds and runtime gating/action tests. Bump local controller89; retain immutable88 receipts.
- [x] Run controller full suite and Installer suite; source-bound local receipt notes untested devices.

### Task3: Mac native acceptance
- [x] Capture fresh private snapshot and installed inventory; confirm idle. Normal ZIP controller install and graceful restart.
- [x] Use real runtime against isolated local test catalog/home: available, notes, Later/restart, Update handoff, partial install no completion, matching test payload completion, Dismiss/no-repeat and preference.
- [x] Capture actual Home-backed screenshots at TV ratio, compare with approved image; fix observed layout issues. Confirm live production state excludes generic add-on notes and keeps real build marker unchanged.
- [x] Compare settings/auth/JSON/watched/resume and installed source; retain private evidence, remove owned test launchers; save local commit only, report native versus automated gaps.

## Acceptance and isolation

Completed on Mac only, 2026-10-24. Source-bound receipt: experiments/release-notices-mac89/acceptance.json. Both native notices and the fixed Installer handoff were exercised with a clearly labeled isolated local catalog/home; the real build marker remains1.1.19. Controller0.1.89 is installed locally. Installer1.0.26 and canonical controller0.1.88 release sources remain unchanged.

The candidate is retained as a nine-file overlay and full file-hash manifest rather than altering canonical release source or weakening old release-gate tests. Final candidate controller suite798 passed; unchanged canonical package suite645 passed. One independent review identified the slow-read deadline and long-notes clipping; both were reproduced and fixed, with final full suite and native scrolling verification.

Full Standard update/new release publication, upstream add-on upgrades, Fire Stick and Apple TV are outside this acceptance. A public rollout still needs the curated catalog published with accurate notes and file proofs, matching edition/version/revision receipts, normal Installer preservation integration and new release gates. No public changes were made.
