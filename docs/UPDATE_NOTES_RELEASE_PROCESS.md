# BlackLanturn update notes

The notice reports changes to actually installed local add-on versions. It does not announce available updates or imply that an upstream upgrade was installed. First startup establishes a quiet baseline. Help and Installer → More tools → What’s new & update notices retain access to history after dismissal or when notices are disabled.

For each release:

1. Review upstream changes against each exact managed patch set. Rebase and test changed source before updating its managed compatibility metadata. Retaining a reviewed old version with Kodi version epochs is protection only, not delivery of newer upstream code.
2. Add short, factual notes to `controller-source/addon/update-releases.json`, keyed by the exact delivered version. Unknown versions receive only before/after version text. Do not include accounts, tokens, usernames or network requests.
3. Regenerate the current controller manifest without rewriting historical receipts. Run controller and Installer suites, clean-install defaults and Standard-update preservation tests. Both editions must contain identical shared notice code while retaining their platform workarounds.
4. Run native acceptance against the exact candidate files. Verify a quiet baseline, a real installed-version change, View changes, Back/Dismiss, persistent preference/history, the branded Installer route, settings and authorizations. Record native and automated evidence separately; source changes invalidate the receipt. Exclude untested devices explicitly.
5. Build both payloads from the verified clean baselines and run `tools/verify_release.py`. Never package a live profile. Publish only after the release is authorized and its device tests pass.

Standard update preserves history and notice preferences. Account-only clean installation starts a new local history. Informational notices defer during playback/previews, loading, settings and dialogs; they never suppress Kodi errors. The original preference snapshot remains available if validation or restoration fails.

Device-specific personal choices belong in preservation checks, not automatically in clean-build defaults.

The upstream rebase/delivery workflow remains separate work. This UI does not automatically merge or validate third-party updates.
