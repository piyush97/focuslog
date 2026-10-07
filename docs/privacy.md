# Privacy and data

focuslog reads the currently focused window's app class and title to estimate whether its activity is study, waste, or neutral. The tracker polls about every five seconds and records local samples in SQLite. This can expose sensitive information because window titles may contain document names, search queries, message subjects, or other content.

## What focuslog reads and stores

- The active window's app class and title from Hyprland.
- A timestamp, sampled duration, and category (`study`, `waste`, or `neutral`) in `~/.local/share/focuslog/focuslog.db`.
- Cached classification verdicts for app-class/title pairs. Manual verdicts are marked as user overrides and survive classifier configuration changes.

focuslog does not take screenshots, record keystrokes, or collect full webpage contents. Window-title inference is imperfect, and a title may itself contain private text.

## Optional hosted classification

With a TypeSafe AI key configured and `[jev].enabled = true`, focuslog can send the configured goal, active app class, and active window title to the Jev endpoint for classification. The default endpoint is `https://api.typesafe.ai/v1/systemone`. The request uses HTTPS and rejects redirects. Known local title/app rules are evaluated before the hosted request according to the [classification order](configuration.md#classification-order). Without a key, the app applies local rules and falls back to `neutral`; it makes no classifier API request.

Review the endpoint and your goal before enabling Jev. Configure only an endpoint you trust. TypeSafe AI's handling of request data is governed by its own policies; consult the provider's current documentation and terms before sending window details.

## Local storage and dashboard

The database contains your activity history and cached verdicts; this project does not document an automatic retention limit. The installer and uninstaller preserve the database and config. Remove or back up those files yourself according to your needs.

The dashboard server binds to `127.0.0.1:47615` by default. It validates the expected Host and Fetch metadata, enables no CORS, and only serves the dashboard and stats routes. These measures are not authentication: other processes running as local users may be able to access loopback services. Do not expose the dashboard through a public network interface or reverse proxy.

The installer stores the optional API key in `~/.config/focuslog/env` with mode `0600`. Protect your account and device accordingly. If you no longer want hosted classification, disable `[jev]` and remove the key from that file.

## Removing data

`./uninstall.sh` removes the installed app/service/UI but intentionally keeps the database, configuration, and API key. To remove local activity history, stop the service and delete the database yourself:

```sh
systemctl --user disable --now focuslog.service
rm ~/.local/share/focuslog/focuslog.db
```

To remove the key, edit or delete `~/.config/focuslog/env`. To remove all user configuration, delete `~/.config/focuslog/` after uninstalling. These actions are destructive; make a backup first if you may need the data later.
