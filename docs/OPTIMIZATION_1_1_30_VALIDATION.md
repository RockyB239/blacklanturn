# Private optimization candidate1.1.30 / Installer 1.0.35

Derived from exact published1.1.29 General and Apple TV/Mac packages; public release remains1.1.29/1.0.34. Controller 0.1.96 has333 manifest-verified source files. Existing reviewed provider patches and platform-native components are preserved. Personal Fight Zone 0.3.4/icons1.0.0 are excluded from public packages.

Shared changes: generic installed extensions/icons, request-scoped nonsecret YouTube settings, bounded latest-only workers, batched disposable snapshots, account-proved RAM-only Trakt display reuse, exact-base component reconstruction/full fallback, interrupted-update cleanup, portable update locks, backend version reports and source-bound performance gates. Fresh normally locked cards batch metadata writes; only immutable main YouTube cards opt into offscreen construction. No displayed-native-object retention remains.

Final suites:933 controller,898 installer,126 personal tests. Unchanged compatibility/tool59 tests passed. Independent final review found no remaining runtime/lifecycle findings. Both complete ZIPs and component packages verify exact source, defaults, dependency/managed-patch contracts and private-data exclusion.

Eight isolated real macOS Kodi cases passed final hashes: two editions × clean/Standard/in-place plus two component updates. Network and personal-profile access were denied and denial proven. General uses simulated Android identity within macOS; no physical Android/tvOS clean-install claim. Live Mac/Fire/Apple in-place updates preserved captured settings/auth and passed exact source parity and100-visit sustained-use checks.

Final comparisons use corrected fresh-row readiness; the earlier protocol could count stale/partially replaced sections and is superseded. Verified code-only baselines and final candidates were both rerun on all three devices; saved data stayed in place. The final comparison and sustained-use gates pass. No universal speedup is claimed. Sanitized final performance evidence is tied to manifest96.json. A rejected native-object-retention experiment and its Fire graphics crash are documented separately in the task report; it is excluded from accepted source/artifacts.

Full ZIPs are approximately91.87MB General and92.69MB Apple/Mac; exact final byte counts and hashes are in the package reports. Exact-base component packages are about12.53MB, roughly86% smaller, and become selectable only when a future published catalog advertises their URLs. Otherwise the normal complete download and validated in-place transaction remain available.

Build with tools/build_release130.py, validate with tools/verify_release130.py against the pinned baselines. tools/release_report.py emits package-derived versions. tools/device_validation/verify_performance_evidence.py validates validation/optimization130-performance.json against controller-source/manifest96.json.

Limits: Apple/Mac resident memory is high-water, Fire current RSS; four warmups precede100 measured visits. No new physical audio/video or complete episode-transition test, no physical Windows test, no automatic arbitrary upstream patching and no public publication. The task report is work/optimization-2026-10-27/RESULTS.md in the project workspace; future features are saved separately at project-root BLACKLANTURN_FUTURE_FEATURES.md.
