# Release 1.1.14 candidate validation

Status: **unpublished candidate; isolated Kodi runtime acceptance pending**. The active public release remains 1.1.13 / Installer 1.0.18. This document is not a device-upgrade receipt.

## Authorized scope

Both existing editions receive shared request reliability/privacy fixes. Preserve platform-specific workarounds, playback/default settings and authorizations; test before updating the public builds. No edition consolidation, personal-device reinstall, app replacement or authorization migration.

## Source and change

Base44852151043a4f1a19a997586142ecfd7bd953b5. Reproducible clean inputs remain the existing hash-pinned public1.1.2 ZIPs; no personal profile is packaged.

The canonical `compatibility/shared-requests/reqapi.py` is byte-identical to the already-published Apple1.1.13 source: SHA256 `9d232490dba165c07fd6ceab42c512ebe90997a794b610fbca14c64429668d59`. The original General source SHA256 is `19351bbe5a5aa7bf9c2f3f893a61ae7effb7ed70afa2d0118d59082e362d0367`.

- HTTP429 uses numeric Retry-After with a60-second minimum; missing/invalid/sub-minute values use60seconds. It schedules suppression rather than sleeping. General previously used the default15seconds.
- Ordinary HTTP401/403/404/422 error logs retain status and hostname, omitting request path/query/userinfo, body, headers and response representation. This is not a claim that every upstream exception/debug logging path has been audited or sanitized.
- Successful response handling is unchanged: no added provider request, wait, worker or background service.

Both editions retain every existing YouTube file byte-for-byte, including their different client choices, trailer workaround, address selection and preview checker. Their existing concurrency limits and all nonreceipt/default userdata are unchanged.

Installer1.0.19 extends the existing managed-addon policy to the complete23-file `script.module.jurialmunkey`0.2.35 tree. It verifies the target archive, accepts only the two known installed request variants with otherwise exact source, checks whitelisted dependencies, and transactionally retains unrelated registry rules while applying the normal per-addon no-auto-update rule. It never pastes an old patch over an unknown newer source. Existing legacy policies remain supported; Installer18 rejects the new policy before device setup or cleanup.

## Automated evidence

- Initial General request tests:11 expected assertion failures covering leaked request details, ignored Retry-After and insufficient cooldown. Exact Apple source then passed all5 behavior tests.
- Managed network/archive/registry/whitelist tests and real Wizard Standard preservation tests were observed failing before the corresponding integration, then passing.
- Full installer/release suite:470tests passed. Controller regression suite:659passed. Native-probe tests:16passed.
- A fresh independent review found no critical/important findings and ran198tests including both deterministic rebuilds. Its minor historical release-note version inconsistency was corrected.
- Final focused network checks:13passed. `git diff --check` passed.
- Exact ZIP comparison against1.1.13 permits only Installer19 source, the canonical request file, release marker and README changes. Every platform-specific YouTube source file and every remaining userdata file matches the public baseline exactly.
- Both candidate ZIPs passed CRC and clean account-field checks. No personal databases, history, logs, sources, favorites or recovery state is introduced.

## Runtime and publication gate

A new disposable copy of Kodi21.3 and its own blank portable profile were created; no personal profile or another task's app was copied or used. Its first network-denied launch proved the task-owned home, but the test did not run because userdata autoexec was not invoked. The owned process was stopped after120seconds. A copied-skin startup hook was prepared to invoke the native test; subsequent launches have been blocked before execution by intermittent automatic approval-review capacity errors.

`tools/verify_release.py` requires a source-bound `compatibility/shared-requests/native-verification.json` before accepting this release. No substitute/synthetic native receipt has been generated. Ordinary HTTP transport is simulated in the test, while RequestAPI dependencies and Kodi property APIs are real; this is separate from physical Fire Stick/Apple TV playback acceptance. The unchanged controller/player evidence remains explicitly historical.

Pending: isolated native result, complete final package gate, final immutable asset hashes, candidate CI, release asset publication/anonymous readback, main/Pages activation. No public release or personal device update has occurred.
