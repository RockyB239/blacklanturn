# Public branded icon packs implementation plan

Goal: distribute the approved Sculpted Silver and Smoked Glass artwork with both public editions, using the existing pack selector. The user explicitly directed inclusion; the visual design is already approved.

Accepted architecture: bundle the exact approved descriptor and 180 PNGs in Controller resources/icon-packs. Controller0.1.97 loads this descriptor before optional external packs. Stable pack IDs preserve explicit Original, Silver or Glass choices; a new installation defaults to Silver. Installer1.0.35 remains byte-for-byte unchanged. The legacy personal resource remains untouched. Fight Zone code and accounts stay private.

Release: new immutable Build1.1.31 from pinned public1.1.30, with both full editions and exact-base30-to31 component archives. Do not replace published30 assets.

- [x] Observe failing omission/default regressions before implementation.
- [x] Copy approved bytes and manifest; implement reproducible131 builder/verifier.
- [x] Native clean, Standard and full in-place cases for both editions, including the first update without a preexisting image addon, saved pack choice and synthetic saved data.
- [x] Complete native component cases, full regression suites, rebuild/privacy checks and final review.
- [ ] Publish exact accepted assets, activate catalog/notes and verify anonymous downloads/CI.
- [ ] Update all three devices through Update BlackLanturn; verify bundled packs, preferences, authorizations and idle screens. Preserve personal Fight Zone and other addons.

Rejected approach: an independent resource addon was tested before publication. Native fresh30-to31 testing proved Kodi can leave a newly introduced image addon disabled under Installer35. Builtin assets avoid new-addon activation/bootstrap complexity and follow the existing original-icon model. Rejected artifacts and the failed acceptance receipt are retained privately; none was published.

Constraints: no artwork redesign, account/default reset, sources/ edit, existing release replacement or unrelated upstream addon update. No additional browsing requests or per-card scans.
