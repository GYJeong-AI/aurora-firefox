# Changelog

## 0.2.2-beta.1

- `bash install.sh` guided setup, read-only regular/Snap/Flatpak profile discovery, one explicit target, cancellation without changes, and explicit non-TTY preview/apply.
- Space/Unicode/shell-metacharacter paths, mode selection, separate experimental GNOME opt-in/restore, running Firefox hints and existing-engine rollback safeguards.
- Public uncompressed source export and allowlist Git ignore; ZIP remains optional. Reviewed public source now includes bilingual README files and an opaque-mode preview.
- Installation UX regression tests added; CSS/SVG behavior unchanged.

## 0.2.1-beta.2

- Staged updates, cooperative operation locks, fsync, interruption records, atomic user.js rollback, original-link identity and stricter manifest validation.
- Experimental GNOME adapter narrowed to GNOME 46 / Blur my Shell 72 / Wayland; typed apply/restore/rollback readback, private backups and shared login lock.
- 50 temporary-profile/mock tests. CSS/SVG behavior unchanged; no new renderer/compositor/performance pass claimed.
- Recovery and supported-matrix documentation; no changes to theme behavior.

## 0.2.1-beta.1 — 2026-10-03

Pre-release audit fixes: preserve/restore relative chrome symlinks, never restore a partial user.js backup before it was modified, reject malformed/incomplete manifests and duplicate pref blocks, guard incomplete GNOME snapshots and rollback failed restore, explicit public-file release manifest, and ignore private QA/local notes in Git. No CSS behavior changes, user-profile reinstall, or GNOME reconfiguration during the audit. Stable release remains blocked on native glass visual and GPU/frame-time validation.

## 0.2.0 — 2026-10-03

Opt-in glass substrate for tab/nav chrome with opaque content and sharp text. Separate existing Blur my Shell configuration helper with exact Firefox-only scope, opacity 255, private settings backup, and guarded restoration. Renderer alpha and UI regression verified; actual spatial backdrop blur comparison remains unverified due compositor capture restrictions.

## 0.1.0 — 2026-10-03

Initial local release: Linux Firefox chrome palette, original traffic light button painting with native geometry and commands, optional top alpha, explicit-profile reversible installer, private backups and deterministic ZIP. Firefox 157 Snap / GNOME 46 Wayland is the tested target.
