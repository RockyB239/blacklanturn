# Mac release notices candidate0.1.89

This is a tested, unpublished Mac-only correction to BlackLanturn release notices. It replaces device-side generic add-on inventory notifications with curated BlackLanturn releases and our release notes. Upstream add-on changes never trigger these notices.

The Mac is running controller0.1.89 through a normal Kodi ZIP install. Its actual build remains1.1.19 and Installer1.0.26. Fire Stick, Apple TV and public release artifacts were not accessed or updated. Settings and authorizations were compared against a fresh private backup.

## Source and reproduction

Base:6d24b6f9fe166151c7e5ffb9ec42e557f5e5e121. `overlay/` contains nine added/replaced source/test files. `manifest.json` binds these files plus every final controller file by SHA256. Apply only to a separate checkout of that base when continuing this candidate; do not overlay onto canonical release source or treat an old release receipt as proof for this candidate. The complete local candidate and ZIP are retained in the project work/release-notices-mac-2026-10-24 folder.

Candidate controller validation: `python3 -m unittest discover -s controller-source/tests`. The unchanged sibling compatibility and branding fixtures from the base checkout must be present. `evidence/controller-tests.log` records798 passing tests. `evidence/canonical-package-tests.log` records645 passing tests for the unchanged accepted release source, not publication acceptance of89.

## Runtime behavior

A bounded cached hourly read checks our curated release catalog in the background. Numeric build versions and patch revisions select the relevant edition. Available offers View changes, Update and Later. Update opens the existing Installer catalog; it never silently installs. Completed requires the advanced installed marker and matching release file hashes. Initial baseline, missing catalog, invalid data and partial payload never invent a success.

A separate release-notices.json migrates the old notice-enabled preference only. Old generic add-on inventory history is excluded. Dismissal and disabling persist. Home/playback/preview/loading/dialog gates remain in place. Long valid notes scroll when focused.

## Native acceptance and limits

Both notices and the sectioned What's new modal were rendered in Kodi over Home and captured in evidence/. View changes, explicit Later, completed Dismiss, notice preference persistence, fresh-interpreter no-repeat, Installer catalog handoff, partial proof rejection and matching minimal isolated payload completion passed. The fixture was explicitly labeled Mac test release, unpublished. It changed only its isolated marker and profile; it did not install Build1.1.20 or change the real receipt.

The cached sample cost measured40 times in Kodi: median0.369ms, max1.961ms. This is not a before/after full Home load benchmark. No inventory RPC or per-row request was added.

One controlled Home trailer changed Kodi's generic local YouTube manifest play counter during testing. With Kodi closed, only that exact row/counter was restored from the fresh baseline after taking an additional SQLite backup. Final settings, saved JSON, watched and resume comparisons match. Temporary owned Favorites and the duplicate Downloads installation ZIP were removed; private recovery data remains outside Git.

## Publication follow-up

The configured releases-v1.json feed is not published by this task. Missing feeds fail quietly. Publication must supply accurate BlackLanturn release notes, edition/version/revision and required file hashes, integrate preservation into the normal Installer release, test the resulting clean/Standard update packages and obtain rollout authority. No third-party upgrades were performed here.

Recovery: the prior controller and userdata archive plus consistent SQLite copies are retained privately in work/release-notices-mac-2026-10-24/private. Reinstall the prior accepted controller through Kodi if needed; restore user state only for a diagnosed difference. Do not replace Kodi, delete profiles or restore old databases broadly.
