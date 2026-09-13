# WGMods page — English

## Title

OldShootSounds — Legacy Gunshot Sounds for Tier I–X

## Short description

Restores gunshot sounds from World of Tanks 1.29.1.1 for recognized standard guns on Tier I–X vehicles, with a choice between the player's tank only or all tanks.

## Full description

OldShootSounds brings the pre-2.0 World of Tanks gunshot sound set back to the current client.

The mod replaces recognized standard firing categories for vehicles from Tier I through Tier X. During installation, you can apply the sounds to the player's vehicle only or to all player, allied, and enemy vehicles. It supports arcade and sniper camera modes, spatial positioning, and standard and double-barrel guns.

Each shot is assembled dynamically from independently randomized historical sound layers, preserving natural variation instead of repeating a small set of complete recordings.

Tier XI vehicles and unknown or special firing systems retain their current sounds. This safety rule prevents a new or unusual gun mechanic from becoming silent.

Only gunshot events are changed. Engines, tracks, impacts, penetrations, non-penetrations, ricochets, shell flybys, reloads, UI, crew voices, music, ambience, destruction, and artillery explosions are not replaced.

## Installation

1. Close World of Tanks.
2. Extract the downloaded ZIP archive.
3. Double-click `Install-OldShootSounds.cmd`.
4. Select the World of Tanks root directory containing `paths.xml`, `res`, and `res_mods`.
5. Choose whether the sounds should apply to all tanks or only to your own tank.
6. Start the game.

The installer detects the active version directory automatically and merges `oldshoot.bnk` into the existing `audio_mods.xml`. Entries belonging to other sound mods or modpacks are preserved.

Run the installer again after each World of Tanks update because the game creates a new active mod directory.

## Hangar test

Press `F8` in the hangar once every 3–5 seconds to cycle through 22 sound events: player and allied/enemy versions of eight standard and three double-barrel categories. The key does nothing outside the hangar and therefore cannot affect battle controls.

The current event is shown in a system message and its playback result is written to `game.log`.

The diagnostic tests all 22 bank events in both installation modes. In player-only mode, allied and enemy sounds still remain unchanged during battle.

## Removal

Close the game and delete the following files from the active `res_mods/<version>` directory:

```text
audioww/oldshoot.bnk
scripts/client/gui/mods/mod_oldshoot.pyc
scripts/client/gui/mods/oldshoot_data.pyc
scripts/client/gui/mods/oldshoot_settings.pyc
```

Remove only the `<bank>` element containing `<name>oldshoot.bnk</name>` from `audioww/audio_mods.xml`.

## Compatibility

- Target game version: `<GAME_VERSION>`
- Other `audio_mods.xml` entries are preserved.
- A mod changing the same gun descriptors may conflict depending on load order.
- The archive does not include crew voiceovers or third-party audio.

## Credits

- Mod author: `<AUTHOR>`
- Source code: `<SOURCE_URL>`
- Original World of Tanks audio and game assets: Wargaming
- Mod version: `<MOD_VERSION>`
