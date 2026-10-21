# Design 1 branding release — 2026-10-20

Approved minimal charcoal frame and cyan orbital lantern. Repository1.0.6 and Installer1.0.21 change only icon.png and their addon version metadata from Repository1.0.5 / Installer1.0.20. Existing repository endpoints, runtime code, layouts, preservation defaults and managed-addon policies are unchanged. The Installer navigation header already consumes its addon icon.

The selected512px RGBA runtime asset is source-controlled in both addon source folders. Rebuild tooling and version assertions now select Installer1.0.21, preserving the branding in future packaging. The immutable published Build1.1.15 payloads and catalog are unchanged. Their Installer minimum remains1.0.20 because21 adds no behavior or compatibility requirement. No existing published ZIP is overwritten except the deliberate unversioned repository bootstrap alias.

Package proof: BRANDING_DESIGN_1_PACKAGE_VERIFICATION.json. This records candidate byte comparisons and ZIP validation, not public availability or native acceptance; those are verified separately after publication and Mac installation.

Recovery: reinstall the preserved Repository1.0.5 and Installer1.0.20 packages. No build reinstall, account reset or playback preference change is required. Fire Stick and Apple TV rollout is deferred until home.

## Publication and Mac acceptance

Release source2cde805 passed candidate/main verification and Pages deployment. All six anonymous public downloads matched exact packaged bytes. Kodi’s native ZIP update installed Repository1.0.6 and Installer1.0.21; both icons were visually confirmed. A normal Quit/relaunch preserved280 active core settings,294 protected configuration files, all saved authorization values, four local history databases and19,905 other addon files. See BRANDING_DESIGN_1_ACCEPTANCE.json.

During initial Repository refresh, unrelated automatic updates replaced the language pack, CocoScrapers and InfoTagger; a native GUI resize crash followed during skin reload. Those three addons were restored from immutable Build1.1.15 bytes proven to match the fresh baseline. The temporary update guard was removed/restored through the native settings API. The native crash itself was not code-patched in this asset-only release. The later ordinary restart and preservation checks passed. Fire Stick and Apple TV were not accessed.

## Catalog follow-up

Both current and legacy catalog self-update headers now advertise Installer1.0.21 and its new versioned ZIP. Their build entries and payload URLs remain unchanged. Repository/bootstrap and standalone Installer downloads use design1, as does the hosted icon used by catalog cards. Published immutable Build1.1.15 archives retain their embedded Repository1.0.5 and Installer1.0.20; a future separately versioned build release is required to update those embedded copies. Historical release assets are not replaced in place.
