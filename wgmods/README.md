# WGMods publication kit

This directory contains text and preparation notes for publishing OldShootSounds on WGMods.

- `page.en.md` — English title, short description, full page text, installation and removal instructions.
- `page.uk.md` — Ukrainian version of the page.
- `moderation-letter.en.md` — English message for WGMods moderation.
- `moderation-letter.uk.md` — Ukrainian translation of the moderation message.
- `legal-and-provenance.md` — asset provenance and relevant Wargaming policy links.
- `submission-checklist.md` — final pre-submission checklist.
- `screenshots.md` — suggested screenshots and captions.

The current Git branch name is the version source of truth and must start with `v<version>`. Building the release synchronizes the root `VERSION` file, creates `dist/OldShootSounds-<version>.zip`, and copies these materials to `dist/WGMods/` with the mod-version placeholder already replaced. Replace the remaining values in angle brackets before submission.
