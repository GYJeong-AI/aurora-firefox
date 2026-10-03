# Installation — 0.2.2-beta.1

From the project directory, run `bash install.sh`. Requirements: Linux, Bash, Python 3.10+ with the standard library. No packages, themes or extensions are downloaded. The interactive prompts currently use Korean.

## Guided setup

1. Choose install/update, removal, status or separate GNOME blur restoration.
2. Choose native, Snap, Flatpak or all registration locations. Discovery reads names and paths in `profiles.ini`; it does not automatically select a default profile.
3. Select one candidate or enter the absolute profile path shown in Firefox `about:support`. Symlinked discovery entries and malformed registration paths are rejected; a manual existing profile may be used.
4. Choose opaque or experimental glass. Glass CSS and compositor blur are separate choices.
5. Review the target, preservation plan and preview; type `APPLY` to commit. Cancellation or EOF before commitment leaves files and settings unchanged.

Discovery locations: `~/.mozilla/firefox`, `~/snap/firefox/common/.mozilla/firefox`, and `~/.var/app/org.mozilla.firefox/.mozilla/firefox`. Recognition does not establish UI compatibility for all package types. No new profile is created. Save your work and close Firefox normally before applying; the installer never forcibly stops it. Restart it normally afterward.

## Explicit commands

If stdin or stdout is not a terminal, action and profile must be explicit; install/update also require a mode. Without `--apply`, commands preview only. Quote paths with spaces. Replace placeholders with your own paths.

```bash
bash install.sh --list-profiles
bash install.sh --list-profiles --distribution snap --json
bash install.sh install --profile "/absolute/path/to/profile" --mode opaque
bash install.sh install --profile "/absolute/path/to/profile" --mode opaque --apply
bash install.sh update --profile "/absolute/path/to/profile" --mode glass --apply
bash install.sh status --profile "/absolute/path/to/profile"
bash install.sh uninstall --profile "/absolute/path/to/profile"
bash install.sh uninstall --profile "/absolute/path/to/profile" --apply
```

`alpha` is the legacy transparency mode; it is not a guarantee of desktop blur. See [blur](BLUR.md) for optional GNOME arguments and [recovery](RECOVERY.md) for interruptions.

## What is preserved

The original `chrome` directory or absolute link is retained in `.aurora-firefox/original-chrome`. For a relative link, `original-chrome-link` retains the original link text and an absolute alias permits access to original files. The original userChrome stylesheet is imported before Aurora; other original files are linked. Existing custom CSS can conflict, so test separately first.

The installer backs up `user.js` and adds one managed CSS-enabling preference block. `prefs.js` is saved as a private recovery snapshot, never edited. History, cookies, logins and sessions are not copied. Backups may contain personal settings: never publish them.

Updates stage a complete theme before replacement, preserve the previous theme and manifest, and keep the initial backup. Managed-file changes, added files or unexpected links stop destructive operations. Locks serialize Aurora commands per profile; do not delete a lock merely because it exists. Cooperative locking does not stop Firefox or other programs from editing files.
