BlackLanturn Fire TV Preview Fix

This build contains the YouTube 7.4.4 client workaround tested on the Fire
Stick. Use InputStream Adaptive and MPEG-DASH for videos are enabled.
The failing android_vr fallback is excluded. YouTube remote watch-history
updates may be affected; Trakt configuration is not changed.

After Kodi starts, BlackLanturn Preview Check runs once after 30 seconds.
It is quiet when the tested configuration is present. It warns if an update
replaces it, the YouTube version changes, or playback settings are disabled.
It never rewrites newer YouTube code or modifies accounts/settings.
Check again manually: Add-ons > Program add-ons > BlackLanturn Preview Check.
It compares the complete client file checksum, not just a visible comment.

Fresh install: link your own services and YouTube, then enable preview
autoplay in the skin when ready. Age-restricted or unavailable videos can
still require YouTube authorization or fail independently of this fix.

When a warning appears: check for an updated BlackLanturn build before
reapplying this workaround. Do not overwrite an unknown newer YouTube version.
YouTube updates can replace the fix; the check detects that on the next Kodi
start or when manually launched. It does not prevent updates.

Recovery: the original pre-fix Fire TV build is retained locally by the
maintainer. Back up your own Kodi profile before a build reinstall; clean
release packages contain no personal account credentials.
