# Current provider compatibility inputs for Build1.1.34

Complete pinned official source archives, upstream and patched file inventories, deterministic wrapped add-on ZIPs and minimal reviewable diffs are retained here. Earlier acceptance packages under current-addons remain historical inputs.

Umbrella6.7.98 retains the existing source-selection, numeric version adapters, progress and approved sanitized default patches. None of the upstream97-to98 changes overlap those patch files.

Helper6.19.2 retains every upstream file, including the new sync-provider architecture. The player/scrobbler merge keeps upstream provider and refresh interfaces plus sampled Kodi timing and early seek/Stop fixes. Trakt and MDbList1.1.0 modules are complete unmodified upstream packages and reuse Helper's existing authorizations.

The compatibility bridge preserves old sync choices without rewriting userdata. Hidden legacy settings remain registered; explicit new provider choices override them. Existing dual-authorized, dual-enabled scrobbling continues sending to both services until a new single-provider choice is made. The context-menu visibility preference keeps its existing setting ID in the new schema and consumer so explicit false survives the upstream rename.

UpNext1.3.0 is unmodified. Branding remains in the unchanged BlackLanturn skin/Controller and personal Fight Zone templates.

Run `python tools/run_current_addons134_contracts.py` from the repository root. This executes the archived release source in temporary directories:50 progress/search/shared-request/migration contracts,12 real SQLite-cache cases and36 Umbrella source-selection/lifecycle cases. No user profile or live service writes are used. Physical-device and exact-artifact native installation evidence is recorded separately for the release.
