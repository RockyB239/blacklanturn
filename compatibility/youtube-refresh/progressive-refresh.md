# Progressive Home refresh — Mac candidate

User-approved local Mac optimization layered on cache/history repair 5314e00. Not published; no other device updated. Keep build and installer version markers unchanged until the release workflow validates finished payloads.

The existing one refresh worker now publishes at most four messages through a bounded queue: recommendations, subscriptions, category catalog, terminal completion/error. Native monitor publication preserves selected title/focus, artwork, resume/watched fields, paging and active category windows. A later failure keeps successful primary rows and the previous categories. Empty subscriptions do not block topics. Watch-status refresh permanently retires queued feed metadata before watch-state hydration, so later queue consumption cannot revert newer progress.

Fresh exact video records fetched by the primary rows are passed only into that same identity-owned Home request. The category adapter resolves missing IDs; category taxonomy checks remain active. There is no added persistent metadata cache or polling job. The existing native one-hour caches and account boundaries remain authoritative.

Validated on Mac: first recommendations published at 7.599 seconds, subscriptions 14.895 seconds, categories 25.552 seconds, complete 25.679 seconds. Baseline complete/first usable refreshed rows 25.762 seconds. Total refresh duration did not improve materially in this sample. Main first publication is about 70 percent sooner. Feed/network/image-cache differences prevent attributing changes in total duration, request count or peak memory to code alone.

744 automated checks passed, including new RED/GREEN cases for staged delivery, late errors, empty subscriptions, cancellation after watch-refresh completion, metadata reuse, selection/cursor retention, native rollback focus and active category retention. Independent review found no remaining important issues. Native tests additionally exercised real continuation (50→100), successful early publication followed by category failure, active category focus, and durable watch cancellation. Detailed performance/resource/preservation evidence is in the project workspace work/youtube-progressive-refresh-mac-2026-10-23/RESULTS.md.

For later distribution, ship these controller changes with the preceding native FunctionCache compatibility repair in both appropriate payloads, retaining existing platform workarounds. Test clean installation and Standard update before publishing. Do not include private test evidence, account stores or Mac settings.

Recovery: close idle Mac Kodi and restore youtube_rows.py, youtube_provider.py and live_review.py from the fresh private/home-before.zip in the evidence directory. The exact original default.py must also be restored if any temporary test entry remains. Do not roll back credentials, settings or history. The previous full cache/history repair remains intact when reverting only these progressive changes.
