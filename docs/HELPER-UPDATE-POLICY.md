# Managed Helper updates

BlackLanturn 1.1.2 ships TMDb Helper 6.17.9 plus the empty-cache-1 correction. A transport failure or malformed response must not be cached as a valid empty list. Successful empty responses retain normal cache behavior. The upstream source and GPL license are retained in `compatibility/helper-empty-cache/upstream-6.17.9.zip`; the two-file patch and full replacement sources sit alongside it.

Installer 1.0.10 verifies the complete reviewed Helper tree before cleanup. Schema 2 makes Installer 1.0.8/1.0.9 reject these packages before cleanup. Update the installer first. Earlier, retired installers must use the existing installer-upgrade path, not direct new payload URLs.

The installer writes Kodi 21's per-addon USER_DISABLED_AUTO_UPDATE rule (1) for `plugin.video.themoviedb.helper` into the existing Addons registry, retains all other rules, and calls UpdateLocalAddons to refresh Kodi's in-memory rules. It does this before cleanup and again after successful extraction. It does not bundle a device database, disable Helper, replace accounts, change global update settings, or add a recurring background service. Partial extraction cannot be marked successful. Full build updates replace Helper with the newly reviewed version and retain the rule.

Kodi source references:
- https://github.com/xbmc/xbmc/blob/21.3-Omega/xbmc/addons/addoninfo/AddonInfo.h (USER_DISABLED_AUTO_UPDATE)
- https://github.com/xbmc/xbmc/blob/21.3-Omega/xbmc/addons/AddonUpdateRules.cpp (IsAutoUpdateable)
- https://github.com/xbmc/xbmc/blob/21.3-Omega/xbmc/addons/AddonManager.cpp (FindAddons refreshes rules)

This protects ordinary automatic and bulk updates. An owner can deliberately bypass it by turning Helper auto-update back on or manually reinstalling a different Helper; that removes the managed compatibility guarantee. Installing a raw payload outside the supported BlackLanturn installer also bypasses installation checks. Older archived builds do not retroactively receive this fix. Existing users update Installer, then install the new build through its catalog using their selected preservation settings.

## Reviewing the next Helper version

1. Obtain the upstream source, retain license and provenance, and compare changes to the two patched parser files.
2. If upstream fixed the bug, use its implementation. Otherwise adapt only the required patch; never replay an old file over an unknown version.
3. Run the native cache regression suite against the exact proposed Helper tree in isolated storage. It must demonstrate recovery after failed responses, non-caching of partial/malformed results, and caching of legitimate empty/populated responses. Record the complete source hashes with fresh results; `native-verification.json` must match the installer manifest.
4. Update `resources/managed-helper.json` only after those checks. Update package baselines, versions and approved provenance intentionally in `tools/build_release.py`. Keep the per-addon protection and schema unless a separately reviewed migration removes them.
5. Run `python3 -m unittest discover -s tests -v`, then `python3 tools/build_release.py --baselines /path/to/verified/baselines --output /path/to/artifacts` and `python3 tools/verify_release.py /path/to/artifacts`. The GitHub workflow repeats these checks; do not publish a failing revision.
6. Native-check the new installer and update-rule behavior on an isolated Kodi 21.3 profile. Verify both package archives, credentials/native exclusions, user-setting preservation, wrapped installer, repository XML/MD5, public bytes and catalog URLs before declaring release complete.

## Recovery

Retain previous release assets and Git commits. Restore prior catalog/installer metadata only with a verified corresponding download. Do not remove the Helper update rule as part of an ordinary rollback to a version still needing this fix. The per-addon setting can be explicitly reversed in Kodi: Add-ons > My add-ons > Video add-ons > TMDb Helper > Auto-update. That opts the installation out of BlackLanturn's reviewed Helper policy.


Release 1.1.3 adds the reviewed search-empty-1 overlay to the exact Helper manifest. It finishes only coherent successful empty searches; errors/cancellations/internal handle -1 remain errors or the original path. Controller source/tests and the provider overlay are maintained in this repository. Installer 1.0.11 is required: 1.0.10 rejects the changed full Helper manifest before cleanup. Fresh native failure-cache evidence for the complete source is recorded; the seven search-completion tests and device search checks cover the added path separately.
