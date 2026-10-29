# Preview Options focus implementation plan

> Use superpowers:executing-plans for inline execution and one final review.

Goal: opening Options must cancel/invalidate owned preview work before Kodi calls yield, keep all menu choices usable, and restart the saved automatic delay after dismissal. No preview preference, playback setting, account, public version or Fire Stick change.

Files: controller-source/addon/live_review.py and title_feedback_ui.py (modal ownership and dispatch checks); controller-source/tests/test_preview_options_focus.py plus the existing episode-options fixture (behavioral regression coverage). Existing monitor interval/cache/network behavior stays unchanged.

- [x] Capture current Mac behavior and confirm shared Apple source; leave active playback alone. Preserve per-device settings/account hashes and installed source backup before edits.
- [x] Reproduce early menu latch, in-flight candidate/publish cancellation, and fresh dismissal delay in failing regression tests.
- [x] Guard menu building before yielding, invalidate preview input epoch, gate lookup/dispatch during menus/settings, reset dwell in cleanup. Keep explicit Preview working outside modals and preserve nested actions/Trakt ownership.
- [x] Run focused and complete Controller tests, one independent review, then native Mac checks: hold menu beyond preview delay, move/select Details, cancel/reopen while a preview is resolving/playing, confirm ordinary preview can resume after normal delay and row navigation remains responsive.
- [x] Install the same bounded source correction on Apple TV and verify its native menu/playback behavior if reachable. Compare protected state on both; keep public packages and Fire Stick unchanged and stage exact candidate for later Fire testing.

Review focus: cancellation while the monitor already passed its top modal guard; menus with unavailable items; nested player/genre/Trakt dialogs; explicit previews; source/UI restoration after native Stop; no settings writes or new polling.

Pre-flight: source and installed Mac live_review.py match current public0.1.99. Apple remote control initially refused; opening existing Kodi is authorized for diagnosis. No Fire Stick connections/actions are used by this task.

Completed evidence: /Users/ChrisFaulkner/.codex/.chatgpt-projects/g-p-6a0726c39718819199402b5f239428f9/work/preview-options-focus-2026-10-28/RESULTS.md and completion.json. 978 Controller tests plus 12 native checks per device pass. Public publication and Fire Stick testing are deferred, not claimed complete.
