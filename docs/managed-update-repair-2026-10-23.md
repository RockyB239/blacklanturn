# Managed add-on update repair — 2026-10-23

Status: unpublished Build1.1.20 / Installer1.0.25 candidate, branch `fix/managed-manual-update-protection`. Public main/catalog remain Build1.1.19 / Installer1.0.24.

## Root cause and repair
Ordinary Mac Kodi21.3 Install all updates replaced patched Helper and Umbrella despite disabled-auto-update rules. All12 same-show source-session contract checks failed afterward. Native Kodi version epochs now protect four managed add-ons; unrelated add-ons still update normally. Exact reviewed metadata and a coupled two-file Umbrella numeric-version/cache adapter are validated before cleanup. Historical inventories remain unchanged; exact adapters normalize only for those historical gates, with the new raw full Umbrella inventory independently pinned. Unknown and partial mixtures reject. No playback/source-selection code, browsing requests or new workers were added.

## Acceptance
- 632 installer tests pass; official native version comparator ordering compiled and tested.
- Disposable native Kodi GUI Install all updates: ordinary positive control 1→2, all four managed add-ons enabled and source-identical despite upstream version 100 candidates, even without update rules.
- Final native clean/Standard production-core tests pass with synthetic account/privacy settings and 3,833 exact add-on files. Public download/catalog delivery has not changed.
- Mac: four managed add-ons and Installer 25 installed through ordinary Kodi Install from ZIP using exact staged code-only addon archives. Its build receipt remains1.1.19. Home, artwork, and four ratings, signed-in YouTube rows, normal automatic 1080p resume and Back/progress verified. 12 copied-source session tests now pass. Every saved XML preference/account grant preserved; only normal short-lived YouTube access token rotation and activity/default serialization occurred.
- Apple visible ordinary update test remains pending because DeviceHub screen streaming fails. Fire Stick untouched.

Machine-readable sanitized source-bound receipt: `compatibility/managed-updates/native-verification.json`. Private full snapshots and account comparisons remain outside this repository in `work/apple-addon-updates-2026-10-23/private`.

## Apple recovery incident and safety boundary
CoreDevice copy-to with remove-existing-content=true affected the entire Kodi app-data container despite specifying an owned temporary snapshot directory. This was an agent error, disclosed immediately. Never use that option again on an Apple app-data container. Do not repeat the destructive test.

Recovered the existing signed Kodi app from the fresh pretest addon/userdata archive and verified saved native XML in the preferences plist, without reinstalling Kodi or modifying management profiles/certificates/network. Readback: 3,831/3,831 original addon source files exact; 35 user-data files exact; all nine virtual XML settings preserved; no missing non-XML files; 26 databases healthy; 106 watched and 18 bookmark cache rows unchanged. Remaining changed files are runtime caches/databases/logs after normal launch. This does not claim visual Apple update/playback acceptance. Recovery snapshots intentionally exclude rebuildable thumbnail/package/bytecode caches.

Use read-only device copy-from for verification. Any future copy-to must explicitly retain existing content and preflight an exact local recovery manifest. Source snapshots and credentials stay private; retain original backup until physical-device acceptance.
