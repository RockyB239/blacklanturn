# BlackLanturn managed add-on updates

For an existing build, update BlackLanturn Installer through its repository, then open Installer → Builds → your installed edition → **Update BlackLanturn**. This is an in-place code update: bundled add-ons and their reviewed patches arrive together. It never runs the build cleanup, extracts userdata defaults, restores a subset of accounts, changes skins, or removes other installed add-ons. Every saved account, preference, source, history database and custom user-data file stays in place; Save Data selections do not apply to this action. Close and reopen Kodi after the update.

Fresh and Standard installations remain separate setup/reinstallation tools. They are not the recommended update action. No separate updater add-on is required.

The update validates the full managed source and final dependency requirements, stages complete bundled code trees, and holds one writer lock through replacement and cleanup. Newer ordinary dependencies and the running Installer stay whole; native components stay owned by Kodi. Existing code is retained in a transaction journal until the batch and release receipt commit. Failed replacements roll back. After a process interruption, reopen Update BlackLanturn to recover the prior complete code before retrying. Nothing is reported complete until code verification and metadata commit finish.


Normal Kodi repository/bulk updates cannot replace epoch-one BlackLanturn managed variants with epoch-zero stock packages, even when stock has a larger ordinary version number. Per-addon automatic-update rules provide an additional guard. This does not disable ordinary updates for unrelated dependencies. An explicit manual downgrade/replacement selected by a user is outside automatic-update protection. Unknown installed managed source stops before cleanup; the Installer does not copy an old patch over unfamiliar upstream code.

Operator workflow:

1. Inspect the actual upstream repository catalogs and archive contents independently of Kodi's Available updates list. An epoch-protected old managed add-on may intentionally outrank a newer stock version, so an empty update list does not mean upstream is current.
2. Pin the complete new upstream archive, URL, SHA256 and full file inventory. Port every existing patch, resolving upstream overlaps and settings/schema changes. Keep platform-specific fixes. Never change an older source's version label to simulate an upgrade.
3. Run current-source patch tests, dependency-minimum checks, both complete package builds, privacy checks, exact-artifact in-place preservation/rollback tests and clean/Standard regression tests. Test source selection/playback on an available appropriate device; distinguish prior unchanged-source evidence from new native acceptance.
4. Update exact managed manifests, approved historical upgrade inputs and the minimum compatible Installer when source policy changes. Unknown source, partial adapters, symlinks and foreign files must refuse before cleanup.
5. Publish immutable tested build payloads and the matching Installer. Verify anonymous downloads against accepted hashes, then activate the catalog and curated BlackLanturn release notes. Important compatibility fixes should say so in the release summary. Notices report BlackLanturn releases, not unrelated addon inventory.

Release 1.1.24 uses Installer 1.0.30, Umbrella 6.7.97 and Helper 6.18.2. Current pinned source contracts run in CI via `python tools/run_current_patch_contracts.py`; the ordinary source suites retain explicit historical evidence rather than pretending it certifies different source. Fresh isolated native install-core proof is required for the exact three published ZIPs, including both editions’ in-place update cases by `tools/verify_current_install.py`.

Standard preserves selected account grants, supported playback and controller choices, Kodi viewing databases, account-scoped YouTube history/bookmarks and their journals. It keeps newer compatible portable ordinary dependencies as complete trees, including dependency minima; it cannot mix old package files into a newer retained tree. The running Installer remains intact. Older/equal bundled own-repository source is replaced completely; newer compatible own-repository source survives Standard. Clean/account-only reset deliberately uses build defaults and clears previous local history while retaining only the accounts selected for that mode. Native IA/PIL files remain platform-owned.

The source/provenance, package checks, native acceptance and public readbacks must be reported separately. Passing a host simulation or a historical receipt is not proof of new physical Fire Stick/tvOS playback. Packaging does not imply every personal device was updated.
