# Current bundled add-ons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish Build1.1.34/Installer1.0.38 with current Kodi21 upstream add-ons and retained BlackLanturn patches; update Mac, Fire Stick and Apple TV in place with verified preservation.

**Architecture:** Keep OpenWizard-based Update BlackLanturn, managed epoch/source protection and two platform editions. Port only demonstrated compatibility deltas onto complete pinned Umbrella6.7.98 and Helper6.19.2 archives; bundle upstream UpNext1.3.0. Keep personal Fight Zone0.3.6 and account data outside public assets.

**Tech Stack:** Python3, Kodi21.3, XML, deterministic ZIP/component packages, GitHub Releases/Pages, native Kodi/ADB/devicectl validation.

**Spec:** User request "get the build and devices up to date"; fresh audit at work/addon-currentness-2026-10-28/audit.json and devices.json under the project workspace; BLACKLANTURN_CURRENT_STATE.md for preservation and current release33 baseline.

## Global Constraints

- Preserve all settings, authorizations, sources, unrelated add-ons, title preferences and watched/resume progress. Use Update BlackLanturn, never profile cleanup/reinstall.
- Retain source-specific YouTube platform variants, branded UI/icons, source-selection/Play Next, Trakt/progress and privacy fixes.
- Keep full exact upstream source; no transplant of entire stale patched files over changed upstream behavior.
- Do not edit sources/ or invalidate historical accepted evidence. New source archives/manifests are separate; current fixture loader selects the latest reviewed manifest.
- Version floors Kodi21.3/Python3.0.1; release34/Installer38/Controller0.1.99 unchanged; Installer38 carries the source guards.

## Review Focus

- New upstream code overlapping our player/progress/cache/autoplay changes retains both behaviors.
- Managed version/source policy accepts reviewed new trees, rejects unpatched/new unknown source, and can upgrade preserved older managed trees.
- In-place/component fallback preserves third-party add-ons and saved data while replacing bundled add-ons atomically.
- Current fixtures must exercise actual newly ported source; historical acceptance remains frozen and honestly labeled.
- Private Fight Zone and credentials stay absent from public packages; all devices reach exact candidate code after restart.

### Task1: Provenance and patch ports

Files: new compatibility/addons134/{upstream,patched,manifest,port-report}; tests/test_current_addons134.py; existing compatibility contracts.
- [ ] Pin complete source archives and compare old upstream→patched versus old→new upstream. Record every overlap.
- [ ] Add new-version/complete-tree/provenance contracts, observe failure against release33 source.
- [ ] Run existing player/progress/cache/source contracts against new upstream candidates, observe missing-patch failures; port minimal deltas using three-way merges and inspect overlaps.
- [ ] Verify unaffected new upstream bytes exact; tests all green; record source hashes and upstream changelog/dependency effects.

### Task2: Managed update protection and packages

Files: Installer managed JSON manifests/policy, current fixture loader, tools/build_release134.py/verify_release134.py, unchanged Controller manifest99, release notes34, CI.
- [ ] Test reviewed new target acceptance, unpatched rejection, old managed migration and preservation before changing manifests.
- [ ] Add new approved metadata/tree records while retaining old variants; update only authoritative current fixture selection, preserve historical manifests.
- [ ] Build both deterministic full34 and33→34 components plus Installer38 from SHA-pinned public33 baselines; proof includes new providers.
- [ ] Verify full source/dependency closure, platform variants, icons/privacy, reproducibility, clean/Standard/in-place/component and interrupted recovery contracts.

### Task3: Native acceptance and review

Files: project work/release134-addons-2026-10-28 native/device harness and evidence; fresh protected snapshots.
- [ ] Verify existing isolated worktree; no duplicate worktree. Create fresh device recoveries including all changing add-ons and native/saved account state.
- [ ] Run full Controller/Installer/compatibility suites and isolated exact-artifact native install cases; retain explicit platform/harness limitations.
- [ ] One fresh focused whole-branch reviewer; one test-first fix pass for material findings.
- [ ] Read-only version recheck before freezing release; no silently stale dependency acceptance.

### Task4: Publish and apply

- [ ] Source commit/push with CI, then immutable5assets publish; anonymous SHA/CRC verification before catalog/repository activation.
- [ ] Activate Installer38 and both34 catalog entries/notes/components; CI/Pages and exact hosted bytes pass.
- [ ] Apply actual public Update BlackLanturn on Mac, Fire and Apple; keep Fire foreground. Preserve private add-ons. Await each completed transaction before restart.

### Task5: Final verification and cleanup

- [ ] Exact changing addon/Installer/Controller source parity, native preferences/account identities, saved settings/progress/DB health and notices ON on all3.
- [ ] Actual provider-row/episode browsing, resume/earlyStop/progress/source-selection and branded UpNext contracts/native UI; matched cached/deep-row speed check without clearing caches. Label any untested full-stream scenario.
- [ ] Final currentness report separates platform-specific intentional variants from missed updates.
- [ ] Remove only owned staging, leave populated idle Home with usable focus; retain restricted host recoveries. Update root current-state/results/completion with limitations.

## Corrective release35 checkpoint

The physical post-restart audit found the two newly copied Helper sync modules disabled. The initial native fixture explicitly enabled them and therefore did not prove automatic registration. Release34 is not accepted as the completed device result.

Installer39 adds a journaled registration phase before metadata/completion commit: enable only newly introduced bundled add-ons, verify exact version/enabled state, restore prior flags on rollback/cold recovery, preserve existing disabled unrelated add-ons. A narrow upgrade from Build34 repairs only its two introduced1.1.0 sync modules; later deliberate disables remain saved. Build35 carries the corrected Installer in both editions. Native fixtures must assert enabled providers without manually enabling them, with33-to35 new-module and34-to35 disabled-provider cases. Original recoveries remain retained alongside fresh34 recoveries.
