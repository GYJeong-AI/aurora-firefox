# Engineering checks — 0.2.2-beta.1

This is a beta, with an experimental optional GNOME blur helper. The checks below cover installer safeguards and packaging; they do not prove universal compatibility or measured performance improvements.

- Complete updates are staged before swapping directories. The preceding theme is retained by rename with its manifest.
- Profile and per-login GNOME operation locks, file/directory synchronization and interruption records limit concurrent and interrupted operations. Ordinary errors, Ctrl+C and SIGTERM attempt rollback; hard interruption records block further automatic changes.
- Manifest paths, hashes, profile identity, flags, originals and nested links are validated. Relative original links preserve their original text. Older manifests cannot retrospectively prove an original target identity they did not record.
- Atomic `user.js` replacement and rollback preserve later edits. Only Aurora's managed preference block is removed.
- GNOME application/restore/rollback use typed readback. Existing non-Firefox application scopes, drift and incomplete backups are rejected. Settings are not one atomic GNOME transaction.
- CSS keeps native geometry and focus indicators, with platform/forced-color guards. Four SVG glyphs contain no executable code or external references.
- The explicit public manifest excludes local profiles, private backups, QA automation and internal logs. One reviewed blank-profile preview is intentionally included.

Run `python3 -m unittest discover -s tests -v` and `bash -n install.sh`. The suite contains 80 temporary-profile/mock tests. See [validation](VALIDATION.md) for evidence and limitations and [recovery](RECOVERY.md) for interrupted operations.
