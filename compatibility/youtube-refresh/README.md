# YouTube cache freshness repair — Mac validation candidate

User approved local Mac testing only. No build, installer, repository or other-device update has been published.

The bundled upstream file is the exact installed YouTube 7.4.4a source before this repair. Its function-cache read path rewrote an unchanged cached value through Storage._set, renewing the fetched timestamp on every visit. The candidate writes only a real fetch or a processing operation. Pure hits retain fetched age; explicit refresh, identical-value refetch, process merging, oneshot removal and disabled-cache behavior are covered.

Controller changes reorder only newly opened recommendation rows using existing local completed status. Unfinished videos lead; completed videos remain available. Loaded/continued rows retain order and focus, including page eviction and error/retry. No added polling or provider requests. Subscriptions/history keep provider order. Artwork and playback URLs remain attached to their original items.

Mac-only setting change: kodion.history.remote false → true through Kodi's add-on API. Normal full videos report history. Existing preview incognito/screensaver routing remains unchanged and was verified to exclude local and remote history.

Before any later packaging, integrate the candidate into the existing managed YouTube patch/update process with the upstream hash guard in receipt.json. Do not copy a Mac account store or settings file into a public payload. Revalidate against any different upstream version instead of blindly overwriting it.

Evidence: work/youtube-refresh-mac-2026-10-22/RESULTS.md in the project workspace. The verified private backup is separate from this Git worktree. Recovery: close idle Kodi, restore the four changed source files from home-before.zip; change only kodion.history.remote back through the add-on settings if reverting that preference. Preserve newly recorded history and normal refreshed access tokens; do not replace whole account or settings stores.
