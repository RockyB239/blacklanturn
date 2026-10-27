# Branded icons release1.1.31

Both public editions now include180 approved PNGs and the descriptor directly in Controller0.1.97. Each file exactly matches the approved artwork source. Builtins load before optional external packs; stable IDs retain the current selection. A new installation defaults to Sculpted Silver and offers Smoked Glass and Original. Installer1.0.35 is byte-for-byte unchanged. No playback or row-loading implementation changes are included.

Acceptance:901 Installer,933 Controller,36 playback,16 probe and7 YouTube context tests passed locally; independent source CI40584938786 passed on commitb094ac7e585dec9533f0efd5ff62f5997772b1ee. All five ZIPs were rebuilt identically. Anonymous public downloads match accepted SHA256 hashes and pass CRC. Native APIs in an isolated macOS Kodi profile passed eight cases: clean, Standard, full in-place and component updates for each edition. Both packs resolve without an external image addon, including the first General update. Explicit Glass, disabled notice preference, synthetic authorization/playback records and unrelated addon data stay intact where preservation applies.

Scope: Android platform identity is simulated in native macOS for installer branching; no physical Android/tvOS clean-install claim. Network and real-profile denial were exercised. Native transport and physical-device updates are separate follow-up checks. Prior1.1.30 speed measurements are retained as historical evidence; this release does not claim newly measured speed improvement. Public assets exclude Fight Zone and all private account/saved files.

An independent resource-addon proposal was rejected before publication because Kodi left the newly introduced image addon disabled in a fresh in-place update. The accepted builtin design avoids that registration dependency. No resource101 or Installer36 was published. Existing personal resource100 is left untouched.

Release: https://github.com/RockyB239/blacklanturn/releases/tag/v1.1.31
