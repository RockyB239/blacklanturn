# Approved update notes design

User approved the mockup and Mac/Apple TV deployment on 2026-10-24. Fire Stick is excluded until explicitly available.

Add a cyan/charcoal Home notice with View changes and Dismiss, plus a remote-friendly What's new dialog with persistent Show update notices preference. Back dismisses. Notes remain accessible from Help and Installer. Defer notices during playback, previews, loading, settings or other dialogs. Do not fetch network data or delay row loading for this feature.

Record installed add-on version changes from Kodi's local installed inventory. Establish a quiet first-run baseline; the new controller may describe its own installed feature without claiming unobserved upgrades. Never announce an available, failed, or merely protected old upstream version as updated. Group actual changes once, retain bounded local history, atomic persistence, no tokens or account data. Exact reviewed release entries may explain retained fixes; unknown updates get factual version changes only. Disable informational notices independently of Kodi errors.

Include shared code in both future build packages and the Installer entry point. Future releases must supply accurate notes, verify installation and preservation, and distinguish upstream rebases from protection-only releases. This feature does not substitute for rebasing/testing upstream releases.

Mac then Apple TV: backup private state, use normal Kodi package install, verify source and settings/auth preservation and native UI. Do not reinstall Kodi, change management profiles, change networks, or touch Fire Stick. Public publication remains a separate release action.
