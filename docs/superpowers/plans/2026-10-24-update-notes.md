# Update notes implementation plan

Spec: ../specs/2026-10-24-update-notes.md

## Global constraints
Use the existing isolated worktree. Preserve all accounts, playback choices and histories. No Fire Stick access or public publication. No network work in the notice path. No false upstream upgrade claims.

## Task 1: Durable local update history
Implement pure update_notes state functions: sanitize inventory, baseline, detect changed installed versions, group, bounded history, atomic save, acknowledge and preference. Test first run, unchanged state, successful changes, missing inventory/error, removal/reinstall, downgrade wording, grouping, dismissal, disabled notices, malformed state and bounded history. Expected: unittest passes after RED-GREEN.

## Task 2: Native notice and notes UI
Implement safe Home-only runtime inventory checks (once after startup off row-loading path, then at most once per 120 seconds), local-only background sampling, no playback interruption, approved visual dialog, manual Help/default.py and Installer entry points. Tests exercise gating, navigation, timeout, preference, thread lifetime and UI screen bounds. Expected: controller tests pass; existing behavior unchanged.

## Task 3: Packaging and release workflow
Version controller 0.1.88 / Installer 1.0.26, keep candidate Build 1.1.20 unpublished; retain immutable historical manifests, add new current manifest and release notes. Both editions must contain exact same notice code and retain their platform workarounds. Add release notes validation and workflow documentation. Expected: installer/controller suites and both package verification gates pass.

## Task 4: Mac and Apple TV native acceptance
Capture fresh protected-state baselines and recovery archives. Install code-only Kodi ZIPs by normal native path. Test notice, View changes, Back/Dismiss, persistent disable and reopen history, settings/auth preservation, navigation/playback deferral. Leave Fire Stick untouched. Expected: exact installed code + preserved protected state + native evidence for both, otherwise explicit remaining limit.

## Review focus
Persistence corruption and partial inventories must never erase prior history or report false success. Notice must not steal playback/input focus, block startup lists, leak account data, or repeat every start. Disabled notices must preserve history access. Installer route must work without reopening Home. Platform-specific playback source stays intact.
