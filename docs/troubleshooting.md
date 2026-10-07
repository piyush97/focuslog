# Troubleshooting

Run commands from a terminal in your Hyprland session. The tracker runs as a systemd **user** service.

## Check service status and logs

```sh
systemctl --user status focuslog.service
journalctl --user -u focuslog.service -n 100 --no-pager
```

To follow new log messages:

```sh
journalctl --user -u focuslog.service -f
```

## Service fails to start

Confirm the required commands and Python version are present:

```sh
python3 --version
command -v hyprctl
command -v systemctl
```

Install requires Python 3.11 or later, Hyprland (`hyprctl`), and a systemd user session. After editing `~/.config/focuslog/config.toml`, validate that it is valid TOML and restart the service:

```sh
python3 -c 'import tomllib; from pathlib import Path; tomllib.loads((Path.home()/".config/focuslog/config.toml").read_text())'
systemctl --user restart focuslog.service
```

Inspect the service log for missing executables, invalid settings, or other startup errors.

## Dashboard does not open

The dashboard server binds to `127.0.0.1:47615` by default. Run:

```sh
focuslog app
```

The app command starts the dashboard server if it is not already listening, then tries the Omarchy web-app launcher, Chromium app mode, and `xdg-open`. If the server is running but no window opens, check that a browser or desktop URL handler is available. If you changed `FOCUSLOG_PORT`, the server and app command must inherit the same value.

The server only accepts the loopback `Host` values it expects and rejects cross-site Fetch metadata. Do not expose or proxy the dashboard on a public interface.

## Dashboard shows no recent activity

Confirm that the service is active and that a supported Hyprland window is focused. focuslog polls about every five seconds; locked sessions and missing active windows are skipped. Focused-window time is not proof of keyboard activity; unlocked idle time can still count. Tracking currently relies on Hyprland and is not supported on GNOME, KDE, or other non-Hyprland window managers.

The database is `~/.local/share/focuslog/focuslog.db`. `focuslog report` can show whether samples have been recorded.

## Categories look wrong

Classification depends on the active app class and window title, so titles that do not describe the actual activity may be misclassified. Add phrases to `[study].title_keywords` or `[waste].title_keywords`, or add app class names under each section's `classes` list. See [Configuration](configuration.md) for classification order.

Use `focuslog mark study`, `focuslog mark waste`, or `focuslog mark neutral` to correct the focused window. The right-click bar action and `SUPER+CTRL+G` binding flip between study and waste. Manual verdicts persist when the goal or auto-classifier settings change. A cached manual label can also explain why a changed rule has no immediate effect.

## Jev does not classify

Jev requires a TypeSafe AI API key in `~/.config/focuslog/env` and `[jev].enabled = true`. Check that the env file contains `TYPESAFE_API_KEY=...`, has mode `0600`, and that `url` uses HTTPS. Check the service log for a Jev request error. Without a key, focuslog uses local rules and `neutral` fallback.

A Jev confidence below `[jev].min_confidence` becomes `neutral`. Redirects are rejected. Failed classifications of the same title wait `[jev].retry_seconds` (300 seconds by default) before trying again. If you change Jev endpoint, model, goal, or rules, non-user cached verdicts are invalidated when classification next runs.

## Omarchy widget missing

Confirm the plugin files exist and validate the installed plugin in Omarchy:

```sh
ls ~/.config/omarchy/plugins/piyush97.focuslog
omarchy-plugin-validate ~/.config/omarchy/plugins/piyush97.focuslog
```

The widget needs the focuslog command installed at `~/.local/bin/focuslog`; the installer sets that up and enables the widget. Restart or reload the Omarchy shell if the widget was just added. On other Hyprland setups, use the Waybar snippet printed by `./install.sh`; it is not installed automatically.

## Config changed or upgrade failed

The installer preserves your settings. If it added Jev settings, it also made `~/.config/focuslog/config.toml.before-jev`. Existing `[llm]` configuration is preserved but ignored; Jev settings belong under `[jev]`. If the service reports a TOML parse error, compare the active config with the backup and correct the TOML syntax, then restart the service.

## Uninstall but keep history

Run `./uninstall.sh` from the source checkout. It removes the installed app/service/UI changes, while preserving the activity database, configuration, and API key. A marketplace Git checkout remains; remove it separately with `omarchy plugin remove piyush97.focuslog` if desired.
