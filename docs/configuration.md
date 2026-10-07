# Configuration

Edit `~/.config/focuslog/config.toml` to change the goal, local classification rules, optional Jev integration, and notification timing. TOML changes are read when the tracker starts; restart the service after editing:

```sh
systemctl --user restart focuslog.service
```

If you installed from a source checkout without running the installer, the program falls back to that checkout's `config.toml` when the user config file does not exist. The installer creates the user config on first run and preserves it on upgrades.

## Example

```toml
goal = "Learn Rust and prepare for systems interviews"
daily_goal_minutes = 180
browsers = ["chromium", "brave", "firefox", "google-chrome", "zen", "helium"]

[study]
title_keywords = ["rust book", "leetcode", "system design"]
classes = ["obsidian", "code", "nvim"]

[waste]
title_keywords = ["reddit", "instagram", "youtube shorts"]
classes = ["discord", "steam"]

[jev]
enabled = true
url = "https://api.typesafe.ai/v1/systemone"
model = "jev-latest"
min_confidence = 0.5
timeout = 10
retry_seconds = 300

[nudge]
waste_minutes = 5
repeat_minutes = 3
```

## Settings

| Setting | Default | Meaning |
| --- | --- | --- |
| `goal` | Example goal in the bundled config | Context for Jev's classification. This text is sent with window details when Jev is enabled and a key is present. |
| `daily_goal_minutes` | `180` | Daily study target in minutes. Set to `0` to disable goal progress and goal-reached notifications. |
| `browsers` | `chromium`, `brave`, `firefox`, `google-chrome`, `zen`, `helium` | App classes treated as browsers for classifier ordering. Match the class value exposed by Hyprland. |
| `[study].title_keywords` | Bundled examples | Case-insensitive substrings in window titles that classify as study. |
| `[study].classes` | Bundled examples | App classes that classify as study when no earlier title/hosted-classifier match applies. |
| `[waste].title_keywords` | Bundled examples | Case-insensitive title substrings that classify as waste. |
| `[waste].classes` | Bundled examples | App classes that classify as waste when no earlier match applies. |
| `[jev].enabled` | `true` | Whether to use Jev when a key is available. |
| `[jev].url` | `https://api.typesafe.ai/v1/systemone` | Jev endpoint. The code requires HTTPS and rejects redirects. |
| `[jev].model` | `jev-latest` | Model name sent to the configured endpoint. |
| `[jev].min_confidence` | `0.5` | Answers below this confidence are treated as `neutral`. |
| `[jev].timeout` | `10` | Request timeout in seconds. |
| `[jev].retry_seconds` | `300` | Cooldown for an unsuccessful classification of a title, clamped to 30–86,400 seconds. |
| `[nudge].waste_minutes` | `5` | Continuous waste time before a notification. |
| `[nudge].repeat_minutes` | `3` | Additional waste minutes before the next notification. |

## Classification order

For a previously cached app-class/title pair, focuslog reuses the stored verdict. Otherwise, it evaluates:

1. Study title keyword.
2. Jev for browser classes, when enabled and a key is available.
3. Waste title keyword.
4. Study app class.
5. Waste app class.
6. Jev for non-browser classes, when enabled and a key is available.
7. `neutral` when no rule or available Jev answer classifies the window.

A cached verdict or manual override short-circuits this sequence. With no key, the Jev steps are skipped.

Manual verdicts created with `focuslog mark` take priority over automatic verdicts. Updating the goal, rules, browser list, or Jev settings invalidates cached non-user verdicts on the next classification; manual verdicts remain.

## Jev API key

During installation, enter a key at the prompt to enable Jev. Press Enter without a key for rules-only operation. The installer reads an existing `TYPESAFE_API_KEY` environment value too, but stores it in `~/.config/focuslog/env` rather than exposing it in the process arguments. The file is set to mode `0600` when written by the installer.

To disable hosted classification, set `enabled = false` under `[jev]`, remove the key from the local env file, or both. If you edit the env file, keep it private:

```sh
chmod 600 ~/.config/focuslog/env
```

Changing a key or endpoint does not itself delete the locally stored activity history. For the information sent to TypeSafe AI, see [Privacy and data](privacy.md).

## Upgrading an older config

When an existing config does not contain `[jev]`, the installer saves a `config.toml.before-jev` backup and appends the bundled `[jev]` defaults to the existing file. It preserves existing fields; a previous `[llm]` section remains but is ignored. Check the backup and resulting TOML if the service does not start after an upgrade. The installer does not overwrite a config that already has a `[jev]` section.
