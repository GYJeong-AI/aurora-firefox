# Recovery — 0.2.2-beta.1

Normally preview `uninstall` and then add `--apply`. Managed-file edits, added files or changed links stop automatic replacement/removal. Preserve edits before resolving them. Never replace current `prefs.js` with an old recovery snapshot.

## Preserved files and links

The original `chrome` directory or absolute link is retained in `.aurora-firefox/original-chrome`. For a relative link, `original-chrome-link` retains the original link text and an absolute alias permits access to original files. The original userChrome stylesheet is imported before Aurora; other original files are linked. Existing custom CSS can conflict, so test separately first.

The installer backs up `user.js` and adds one managed CSS-enabling preference block. `prefs.js` is saved as a private recovery snapshot, never edited. History, cookies, logins and sessions are not copied. Backups may contain personal settings: never publish them.

Updates stage a complete theme before replacement, preserve the previous theme and manifest, and keep the initial backup. Managed-file changes, added files or unexpected links stop destructive operations.

## Automatic handling and limits

A per-profile `.aurora-firefox.lock` serializes Aurora operations. It remains as an empty file; existence does not mean a command is still running. Do not delete it during operations: another inode could permit concurrent locks. Kernel locks are released when the process exits.

Updates retain `previous-chrome` and `previous-state.json` in the transaction directory. Ordinary errors and Ctrl+C/SIGTERM attempt rollback. SIGKILL or power loss may leave `operation.json` or incomplete state; subsequent commands refuse changes. Preserve records rather than deleting them to retry. All combinations of filesystem or rollback failures are not guaranteed. External editors do not honor Aurora's lock.

## Return to the original theme

1. Save work and close Firefox normally.
2. Preserve the current `chrome`, `user.js` and `.aurora-firefox` in a safe private location. Removal may already have renamed state to `.aurora-firefox-backup-<timestamp>`. Do not publish backups.
3. Inspect the interrupted operation and compare originals before changing files. If an initial backup was interrupted and the original is still intact, do not overwrite it with an incomplete copy.
4. Move current `chrome` aside instead of deleting it. If `original-chrome-link` exists, restore **that link itself** to the profile's `chrome` path; its relative target is interpreted from the profile directory. Otherwise restore `original-chrome` itself, directory or link. Do not move/delete a symlink's target. If `had_chrome=false`, there was no original chrome to restore.
5. Remove only the BEGIN/END AURORA FIREFOX block from current `user.js`, keeping subsequent user edits. If removal was interrupted after moving `user.js`, inspect `uninstall-user.js` for the latest version; work on a copy and remove only the managed block. Do not blindly overwrite with `original-user.js`.
6. Keep the records and displaced theme. In `about:config`, restore `toolkit.legacyUserProfileCustomizations.stylesheets` to its prior value if necessary. Restart normally and verify the original UI. Preserve existing state under another name before attempting a fresh installation preview.

To restore the preceding Aurora update instead, restore its `previous-chrome` and `previous-state.json` **as a pair**. Do not mix versions or remove only the operation record. If the pair is absent or further edits exist, use original-theme recovery. Preserve evidence and seek help if uncertain.

## GNOME helper

This helper is separate from profile installation. Per-login commands use a shared lock. New application requires GNOME 46 / active Blur my Shell 72 / Wayland; restore retains validation but does not use the new-application version gate.

Keep backups in an absolute private directory (700), with the backup file at 600. Preview `restore-blur`, then add `--apply`. Drift, pending/incomplete state or malformed backups block automatic changes. Application, restore and rollback read settings back to verify them.

GNOME settings are not one atomic transaction. If rollback fails, compare the preserved original and current values, then restore only the recorded Firefox application-blur keys. Do not delete the backup to retry or overwrite another app's blur scope. See [blur commands](BLUR.md).
