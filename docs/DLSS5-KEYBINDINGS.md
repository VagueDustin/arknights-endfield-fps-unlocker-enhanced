# DLSS 5 keybindings

The Fate Engine default for the tested RenoDX DLSS5 setup is **Insert**, confirmed working in Endfield by the user. F6 conflicts with an in-game menu.

The addon setting in the game's `ReShade.ini` is:

```ini
[RenoDX.DLSS5]
NRToggleKey=45
```

45 is the Windows virtual-key code for Insert. Merge this key into the existing section; preserve the other settings. Restart the game after editing the file externally. Home opens ReShade; skip the first-run tutorial to dismiss its setup banner.

This is the default for the experimental NR setup, not a claim that the published FPS installer includes or configures the addon. Future NR installer integration should seed Insert only when no existing user binding is present.
