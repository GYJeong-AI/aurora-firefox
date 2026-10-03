# Release status — 0.2.2-beta.1

**Beta source; optional GNOME blur is experimental.** Guided Bash setup and explicit non-TTY commands wrap the existing installation/recovery engine. No new CSS behavior is introduced in this version.

- 80 automated temporary-profile/mock tests cover installation, restoration, safeguards, guided setup and public packaging.
- Prior Firefox 157 Snap / GNOME 46 Wayland UI checks apply to the unchanged theme; no fresh renderer/compositor performance pass is claimed.
- Public source and optional deterministic ZIP use an explicit file allowlist. A single reviewed blank-profile screenshot illustrates opaque mode.
- Bash syntax is checked. ShellCheck was unavailable.

Stable-release blockers are native blur off/on visual comparison, compositor popup/maximize/black-artifact checks, controlled GPU/frame-time measurement, actual accessibility and an explicit broader Firefox/package/desktop compatibility matrix. The current support scope is intentionally narrow. These blockers do not prevent publishing a clearly marked beta.

For a manual blur comparison, use a blank test window in front of a high-contrast background. Fix position, size and scaling. Compare compositor blur OFF/ON screenshots without personal pages or other private content. Only the backdrop should spread spatially; text, icons and web content should remain sharp. Check maximization and menus too. This is visual evidence, not a GPU benchmark.

[Installation](INSTALLATION.md) · [Validation](VALIDATION.md) · [Blur](BLUR.md) · [Recovery](RECOVERY.md)
