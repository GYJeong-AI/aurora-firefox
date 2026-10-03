# Validation scope — 2026-10-03

## Release status

**0.2.2-beta.1 is beta source; the optional GNOME blur helper is experimental.** Guided Bash setup and explicit non-TTY commands wrap the existing installation/recovery engine. No new CSS behavior is introduced in this version. The checked scope permits a clearly marked beta; stable release still requires the compositor, performance, accessibility and broader compatibility checks listed below.

## Environment and prior UI checks

Firefox 157.0 Snap revision 8995, Ubuntu 24.04.5 LTS, GNOME Shell 46.0, Mutter 46.2 and Wayland. The Firefox QA renderer reported Wayland. Blank test profiles were separate from personal browsing profiles.

Prior checks covered 15 renderer UI scenarios plus native inactive-window and close-button checks. Theme CSS/SVG behavior is unchanged in 0.2.2-beta.1; these UI checks were not rerun for this packaging/documentation update.

| Check | Result and scope |
| --- | --- |
| Native geometry | Button hit areas, tab and navigation heights matched baseline |
| Light/dark and hover | Palette, colored circles and small glyphs rendered |
| Window controls | Minimize, maximize/restore, fullscreen and close operated on test windows |
| Vertical tabs | Native mode and its maximize/restore controls checked |
| Menus | App-menu open state checked; separate native popup surface not visually validated |
| 125/150/200% | Simulated UI scale and hit-testing checked; physical mixed-monitor DPI untested |
| Glass renderer | Empty tab/navigation pixels alpha 163/255 and 194/255; content 255/255; text unfiltered |

The public preview is an unchanged image of a blank opaque-mode QA window. The striped address bar is Firefox's remote-control indicator, not part of Aurora.

## Installer and package checks

The 80-test suite uses temporary profiles/processes and mocked GNOME settings. It covers preservation of original directories and absolute/relative links, update/removal, later user edits, malformed manifests, symlink guards, operation locks, staging failures, interruptions, rollback and readback failures. Guided discovery/selection, Unicode/spaced paths, cancellation, non-TTY preview/apply and partial blur failures are included.

Package tests enforce the explicit public manifest, Git ignore allowlist, deterministic ZIP and source-export edit protection. The manifest excludes local profiles, private backups, QA automation and internal logs. Bash syntax is checked separately. ShellCheck was unavailable and was not installed. Test counts and package checks do not establish compositor or browser compatibility beyond the stated UI scope.

## Installer safeguards

- Complete updates are staged before swapping directories. The preceding theme is retained by rename with its manifest.
- Profile and per-login GNOME operation locks, file/directory synchronization and interruption records limit concurrent and interrupted operations. Ordinary errors, Ctrl+C and SIGTERM attempt rollback; hard interruption records block further automatic changes.
- Manifest paths, hashes, profile identity, flags, originals and nested links are validated. Relative original links preserve their original text. Older manifests cannot retrospectively prove an original target identity they did not record.
- Atomic `user.js` replacement and rollback preserve later edits. Only Aurora's managed preference block is removed.
- GNOME application/restore/rollback use typed readback. Existing non-Firefox application scopes, drift and incomplete backups are rejected. Settings are not one atomic GNOME transaction.
- CSS keeps native geometry and focus indicators, with platform/forced-color guards. Four SVG glyphs contain no executable code or external references.

For interrupted operations, preserve originals and follow [recovery instructions](RECOVERY.md).

## Remaining limits

- Native spatial blur, black surfaces, compositor popup/maximize visuals and controlled GPU/frame-time costs are unverified. Renderer alpha is not compositor blur evidence.
- Real OS dragging, accessibility/high-contrast/keyboard-only/screen-reader use, RTL layouts and physical mixed-monitor scaling remain unverified.
- ESR, other Firefox releases, deb/Flatpak UI, X11, other desktops/GTK themes and extension versions are unverified. WhiteSur is not a source dependency; a separate clean system without that installed theme was not tested.
- Locks cover cooperating Aurora commands, not all external writes. All combinations of power loss, filesystem behavior, disk exhaustion or failures during rollback are not guaranteed.
- Browser internal CSS has no stable update API. File size and absent background processes are not performance benchmarks.

## Manual blur comparison

Use a blank test window in front of a high-contrast background. Fix position, size and scaling. Compare compositor blur OFF/ON screenshots without personal pages or other private content. Only the backdrop should spread spatially; text, icons and web content should remain sharp. Check maximization and menus too. This is visual evidence, not a GPU benchmark.

## Check after Firefox updates

1. Save work and restart normally; confirm buttons, tabs and address bar.
2. Check light/dark and inactive-window colors.
3. Use a blank window to check minimize, maximize, restore, close and fullscreen.
4. Check dragging, menus, address suggestions and vertical tabs.
5. Check your actual monitors/scaling and click targets.
6. Compare with native Firefox if something breaks. Use [removal/recovery](RECOVERY.md) rather than relying on a browser downgrade.

[Installation](INSTALLATION.md) · [Blur](BLUR.md) · [Recovery](RECOVERY.md)
