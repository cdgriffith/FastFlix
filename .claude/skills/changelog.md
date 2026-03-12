---
name: changelog
description: Update the CHANGES changelog file with new entries. MUST be consulted whenever adding, modifying, or removing entries in the CHANGES file, including when referencing GitHub issues.
user_invocable: true
trigger: Always read this skill BEFORE writing any changelog entry. Triggered by any task that involves updating the CHANGES file, adding a fix/feature note, or referencing a GitHub issue in the changelog.
---

# Changelog Skill

When updating the `CHANGES` file, follow these rules:

## Entry Format

Each entry is a single bullet point starting with `* `:

```
* {Verb} {description}
```

## Verbs and Ordering

Entries MUST use one of these four starting verbs, and MUST appear in this order within each version section:

1. **Adding** — new features
2. **Changing** — modifications to existing behavior
3. **Fixing** — bug fixes
4. **Removing** — removed features or deprecated items

## GitHub Issue Entries

- Entries that reference a GitHub issue include the issue number after the verb: `* Fixing #725 description...`
- Within each verb group, entries WITH issue numbers come FIRST, sorted by issue number ascending (smallest to largest)
- Entries WITHOUT issue numbers follow after

## Thanks Attribution

- When an entry references a GitHub issue, thank the issue author by their **GitHub display name** (not username)
- Look up the display name via `gh api users/{username} --jq '.name // .login'`
- Format: `(thanks to {display name})`
- If multiple people contributed (e.g., reporter and commenter with the fix), thank all of them
- The thanks attribution goes at the end of the entry

## Example

```
## Version 6.2.0

* Adding #731 OpenCL Support setting (thanks to sks2012)
* Adding FFmpeg 8.0+ version check on startup
* Adding "Keep source format" option to Audio Normalize
* Changing visual crop window to show rotated frame
* Changing -fps_mode to be used instead of deprecated -vsync
* Fixing #725 encoder detection to use ffmpeg -encoders (thanks to Davius and Generator)
* Fixing #730 subtitles tab missing on ARM (thanks to enaveso)
* Fixing cover extraction blocking video load
* Removing -strict experimental from SVT-AV1 encoders
```
