# Release 1.1.14 candidate validation

Status: **published release assets and validated source**. Local isolated Kodi acceptance and both candidate/tag CI runs passed. The three public1.1.14 assets were downloaded anonymously and exactly match the frozen SHA256, size and ZIP CRC checks. Main/Pages activation is a separate distribution checkpoint; the live installer catalog identifies the active release. This document is not a personal-device upgrade receipt.

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

A new disposable copy of Kodi21.3 and its own blank portable profile were used; no personal profile or another task's app was copied or used. All network access was denied by the native sandbox. Initial fixture attempts did not execute autoexec or found copied dependencies disabled; the final fixture uses a copied-skin startup hook, standard local-addon refresh and the normal enable-addon API. No product source was changed for those fixture corrections. Failed attempt records are retained locally.

The actual Kodi21.3 run passed for both exact packaged request sources. Each honored120seconds from Retry-After, applied the60-second fallback/floor, suppressed repeat requests without sleeping, and redacted ordinary HTTP-error details. Each returned the identical successful response for10000 synthetic calls with no extra transport calls; elapsed times were0.004061s General and0.004179s Apple. These are synthetic branch timings, not end-to-end browsing benchmarks. No new worker/background thread is introduced. The disposable app exited normally after1.1seconds; actual module paths and the task-owned home were verified. Personal-profile access was false.
`tools/verify_release.py` requires a source-bound `compatibility/shared-requests/native-verification.json` before accepting this release. The receipt records an actual Kodi runtime with synthetic transport outcomes; it is not a physical-device playback receipt. Ordinary HTTP transport is simulated in the test, while RequestAPI dependencies and Kodi property APIs are real; this is separate from physical Fire Stick/Apple TV playback acceptance. The unchanged controller/player evidence remains explicitly historical.

The complete final package verifier passed, including source-bound shared-network evidence. Candidate/tag CI and anonymous public asset readback passed. Main/Pages activation follows the verified assets; the live catalog is authoritative. No personal device update has occurred.

## Exact candidate artifacts

- `BlackLanturn-Apple-TV-Mac-Kodi21-1.1.14.zip`: SHA256 `5ebe0592a91476ee0a03645bd996d996eeeb2384724fa15823f293a0c32adf5c`, 91860884bytes.
- `BlackLanturn-General-Kodi21-1.1.14.zip`: SHA256 `d52962f9fe3cbf096d377cb819c59d7dbe4925577a45f154af84d1d0d9730655`, 91045339bytes.
- `plugin.program.blacklanturninstaller-1.0.19.zip`: SHA256 `555dfe2ac992663fc988770235526a65f1427d50e9c8cf3ea118483cdb4021d5`, 3748315bytes.

## Publication evidence

Release: https://github.com/RockyB239/blacklanturn/releases/tag/v1.1.14 . Tag/source commit: `4ea3db481f58341688e63754cddc1178f9e6c1a9`. Candidate CI39203460429 and tag CI39203797832 succeeded. All three uploaded server SHA256 digests and sizes matched, followed by complete unauthenticated downloads and ZIP CRC checks. Catalog activation is allowed only after this evidence; no personal device install is part of this release operation.
