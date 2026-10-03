# Experimental glass and compositor blur

Opaque mode is the default. Glass exposes translucent tab/navigation surfaces; it does not implement desktop blur itself. It removes opaque backing from the Firefox root/body/toolbox, uses tab alpha 0.64 and navigation alpha 0.76, and keeps web content opaque. Text and icons are not filtered. Glass rules are excluded in fullscreen, customization and forced-color modes.

## Supported new application

The separate helper requires **Linux Wayland, GNOME 46 and an already ACTIVE Blur my Shell 72**, with existing `gsettings`, `gnome-shell` and `gnome-extensions` commands. It does not install or upgrade the extension. Other compositors are not configured.

Use a separate test profile first. Verify the exact window class on your own desktop; do not infer it from packaging. Allowed class names are `firefox`, `firefox_firefox` and `org.mozilla.firefox`, but the correct subset must be directly confirmed. Wildcards are rejected. Existing application blur that includes other apps is rejected rather than overwritten.

Use a new backup path in an existing private directory with permissions 700. The backup is written with permissions 600. The same arguments without `--apply` only preview:

```bash
bash install.sh install --profile "/absolute/path/to/profile" --mode glass --gnome-blur --wm-class firefox --blur-backup "/absolute/private/path/glass-settings.json"
bash install.sh install --profile "/absolute/path/to/profile" --mode glass --gnome-blur --wm-class firefox --blur-backup "/absolute/private/path/glass-settings.json" --apply
```

Add repeated `--wm-class` arguments only for directly confirmed Firefox classes. The guided flow also offers a separate opt-in. Profile installation happens before compositor application; if blur fails, the tool reports the partial result instead of claiming full success.

## Settings and restoration

The helper uses native dynamic Gaussian BACKGROUND blur, sigma 18, brightness 1.0, whole-window opacity 255, `enable-all=false`, exact Firefox whitelist, `dynamic-opacity=false` and `static-blur=false`. It changes application blur settings only. A blur actor may span the whole window even when only the top is visibly translucent; this has not been performance-optimized or benchmarked.

```bash
bash install.sh restore-blur --blur-backup "/absolute/private/path/glass-settings.json"
bash install.sh restore-blur --blur-backup "/absolute/private/path/glass-settings.json" --apply
bash install.sh update --profile "/absolute/path/to/profile" --mode opaque --apply
```

Restart Firefox normally. Settings drift and incomplete backups block automatic restoration. Restoration does not require the exact version gate used for new applications, but still validates the backup and current state. Each new opt-in should use a fresh backup path. See [recovery](RECOVERY.md).

## Unverified behavior

Renderer alpha, opaque content, unfiltered text and existing UI regression checks were verified. Native spatial backdrop blur, popup/maximized compositor surfaces, black artifacts and controlled GPU/frame-time cost remain unverified: compositor capture was unavailable. Renderer PNGs cannot establish blur success. If you see artifacts or stutter, restore the compositor backup and return to opaque mode. Do not describe transparency alone as successful blur.
