# Release35 Helper selection follow-up

Complete Helper6.19.2 source with the reviewed release34 patches and one additional correction: an explicit provider choice is persisted even when it matches the legacy fallback. This lets a dual-service legacy user explicitly select only Trakt. Stored account or playback settings are not rewritten during installation.

The upstream archive remains pinned under addons134; release34 artifacts remain unchanged. The managed metadata stays1:6.19.2+blacklanturn.1; full source manifests and Build1.1.35 distinguish the tested patch revision. Installer39 accepts the prior reviewed installed tree for migration and only the new tree as the incoming target.
