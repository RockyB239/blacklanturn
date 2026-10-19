# Shared request reliability and privacy implementation plan

**Goal:** Give both BlackLanturn editions the reviewed request cooldown and sanitized HTTP-error logging without changing platform workarounds or personal data.

**Architecture:** Maintain one hash-pinned request source and apply it to both reproducible builds. Extend the existing managed-addon checks and per-addon Kodi update rules to the shared dependency, using Installer 1.0.19 and build 1.1.14. Keep both edition IDs and all native components unchanged.

**Spec:** Chris's authorized request in this chat, following the verified 1.1.13 edition comparison. Scope is shared reliability/privacy code and its release/update protection, not edition consolidation or personal-device reinstalls.

**Execution:** Authorized inline execution; no further design approval required for this narrowly scoped repair. Use systematic debugging, test-first implementation and fresh review before publication.

## Constraints

- Kodi 21.3; existing OpenWizard installer and branding/IDs.
- Source builds exclusively from hash-pinned clean release inputs, never personal profiles.
- Preserve all existing playback/default/userdata bytes except build receipt and release notes.
- Preserve complete platform-specific YouTube trees and processing defaults.
- No operations on personal devices needed for host/isolated runtime acceptance; no clean installs or app replacements.

## Review focus

- Rate-limit headers: numeric, missing, invalid and sub-minute values must suppress retries without blocking the GUI.
- Credential-bearing URL, headers, body and response must not appear in ordinary HTTP-error logs.
- Successful requests must return the original response without extra network calls or waits.
- Damaged/missing shared code must fail preflight before cleanup; whitelist cannot retain an outdated managed dependency.
- Standard updates retain decoder/language/Trakt/YouTube preferences and authorization grants; unrelated addon update rules remain intact.

## Tasks

1. [x] Add real RequestAPI behavior tests; reproduce General cooldown/logging defects, then use the already-reviewed Apple source as common canonical code. Record exact provenance.
2. [x] Add optional managed shared-dependency archive/whitelist/update-rule checks and policy tests; integrate Installer19 and reproducible build14. Keep legacy build policies supported. Run full regression suites.
3. [ ] Test both exact candidate ZIPs in an isolated Kodi runtime, verify unchanged settings/defaults/platform code, run release/privacy gates and fresh review. Only then publish immutable assets and update catalogs after current GitHub baseline checks pass. Do not change personal device apps/data.

## Ledger

- Initial evidence: General request source SHA19351bbe5a5aa7bf9c2f3f893a61ae7effb7ed70afa2d0118d59082e362d0367; Apple SHA9d232490dba165c07fd6ceab42c512ebe90997a794b610fbca14c64429668d59. Same dependency version0.2.35 and all other dependency files match.
- GitHub baseline read through automatic approval review failed due model capacity; not executed. Local isolated clone at4485215 created; no public/device changes.

- Task1 complete: ordinary request-error privacy and Retry-After tests reproduced11 General failures; exact existing Apple source passed all5 behavior tests.
- Task2 complete: complete23-file shared dependency manifest, transactional/idempotent update rule, pre-cleanup archive/installed/whitelist guards, legacy Installer18 rejection and real Standard preservation tests. Complete installer/release suite470 passed; controller659 and native probe16 passed.
- Independent whole-change review found no critical/important issues (198 reviewed tests passed); corrected the sole historical release-note version inconsistency.
- Task3 pending: both ZIPs preserve all platform YouTube source and nonreceipt/default userdata exactly against1.1.13, clean account-field/privacy scan passed. First disposable Kodi launch proved21.3 and task-owned home but userdata autoexec was not invoked; owned process terminated on120s bound and startup hook corrected. Subsequent launches await automatic approval review (capacity failures). No personal device or public release changes.
