# WGMods submission checklist

## Metadata

- [ ] Replace `<AUTHOR>` in both page texts and moderation letters.
- [ ] Confirm that the version generated from the root `VERSION` file is correct.
- [ ] Replace `<GAME_VERSION>`.
- [ ] Replace `<SOURCE_URL>`.
- [ ] Select the Sounds category.
- [ ] Add English as the primary description and Ukrainian as the additional description.

## Files

- [ ] Rebuild `dist/OldShootSounds-<version>.zip` from the final commit.
- [ ] Create the matching `v<version>` Git tag after the final commit and validation.
- [ ] Record the ZIP SHA-256 checksum.
- [ ] Confirm that the archive contains no development folders, old client packages, extracted WEM files, logs, replays, or `voiceover.bnk`.
- [ ] Confirm that `Install-OldShootSounds.cmd` only launches `Install-OldShootSounds.ps1`.
- [ ] Confirm that the PowerShell source remains readable inside the archive.
- [ ] Scan the release archive with current antivirus software.

## Testing

- [ ] Test installation with a clean `audio_mods.xml`.
- [ ] Test installation when `audio_mods.xml` already contains other banks.
- [ ] Confirm that installing twice creates only one `oldshoot.bnk` entry.
- [ ] Complete all 22 F8 events in the hangar.
- [ ] Test player and enemy shots in a replay.
- [ ] Test arcade and sniper camera modes.
- [ ] Test a standard single-barrel Tier X vehicle.
- [ ] Test at least one double-barrel vehicle.
- [ ] Test a newly added Tier I–X vehicle.
- [ ] Confirm that a Tier XI vehicle keeps its current gunshot sound.
- [ ] Review `game.log` for OldShootSounds errors.

## Page and moderation

- [ ] Add screenshots listed in `screenshots.md`.
- [ ] Paste the applicable text from `page.en.md` and `page.uk.md`.
- [ ] Send `moderation-letter.en.md` with the submission.
- [ ] Clearly credit Wargaming for the original World of Tanks audio.
- [ ] Mention the hangar-only F8 diagnostic key.
- [ ] Mention that the installer merges `audio_mods.xml` and preserves other entries.
