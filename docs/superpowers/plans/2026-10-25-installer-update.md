# Integrated Installer Update Implementation Plan

> **For agentic workers:** Execute approved tasks using test-driven development. Independent Installer transaction and release-evidence tasks use parallel agents; root owns Controller recovery and publication.

**Goal:** A BlackLanturn update includes the Installer without a separate manual repository step after this capability is installed.

**Architecture:** Extend the existing staged in-place transaction to include the Installer, applied last and recovered first. A controller-owned startup entrypoint can recover a missing Installer from its backup. End the outgoing Installer invocation after update; Kodi registers complete code and the user restarts normally. No separate updater add-on or saved-data reinstall.

**Tech Stack:** Kodi21.3 Python3, existing OpenWizard foundation and journal/OS lock.

**Spec:** Approved user request and preceding explanation in this chat. Preserve all saved data and unrelated add-ons; publish both editions; leave personal devices untouched to observe notifications. Existing Installer31 cannot gain this capability before it receives32 through its normal repository update.

## Global Constraints
- Build1.1.27, Installer1.0.32, Controller0.1.94; min supported update-format30.
- Preserve older release artifacts/evidence and platform workarounds.
- No live device modification; only disposable native Kodi tests.

## Review Focus
- Power loss after the outgoing Installer directory moves away: controller bootstrap must recover it.
- Interrupted recovery must be repeatable and ordered independently of sorted JSON.
- Newer user-installed Installer versions must not be downgraded.
- Close later must end old Installer Python navigation.
- Playback, failed staging, full disk and foreign dependencies must retain existing behavior.

### Task1: Protected Installer transaction
- [ ] Write real tree failure/success tests; observe red.
- [ ] Include SELF last, retain newer versions, recover SELF first.
- [ ] End outgoing navigation; test Close later/failure.

### Task2: Independent Controller recovery
- [ ] Write missing-target, active-target, interrupted recovery, linked path and active-lock tests; observe red.
- [ ] Load only the existing active/backup Installer's fixed recovery core when an actual SELF journal exists.
- [ ] Recover before normal controller startup; show bounded actionable failure if needed.

### Task3: Release acceptance
- [ ] Freeze versions/source manifests; build both editions and Installer ZIP.
- [ ] Full controller/Installer suites, exact packages, isolated native normal update/selfswap/recovery/startup tests.
- [ ] Independent review and reproducible/privacy validation.
- [ ] Source CI, publish exact assets, anonymous readback, then activate notification/catalog/repository feeds.

Recovery-capability guard: replacing the Installer itself requires existing Controller0.1.94+ and its recovery entrypoint. The initial full27 update with Installer32 unchanged remains supported. This ensures an older Controller cannot be restored without the pending-registration retry hook.
