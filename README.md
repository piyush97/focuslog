# focuslog

Study-vs-time-waste tracker for [Omarchy](https://omarchy.org) Quattro: background tracker, desktop dashboard app, and native Quickshell bar plugin. Classification by **Jev (TypeSafe AI)**.

## How it works

- **Tracker** (`focuslog run`, systemd user service): samples the focused window every 5 s via `hyprctl activewindow -j`. Locked screen (Quattro shell lock / hyprlock) isn't counted.
- **Classifier**: your keyword rules first (instant, free) → [Jev](https://docs.typesafe.ai) `choice` question (`study` / `waste` / `neutral`) with your `goal` as context. Below `min_confidence` → neutral. Each title is classified **once** and cached, so Jev costs stay tiny. Without a key → rules only.
- **Nudge**: 5 min continuous waste → critical Omarchy notification, repeating every 3 min until you go back.
- **Bar plugin** (`piyush97.focuslog`): `󰑴 1h20m · 14m` (study · waste), urgent color when focus < 50 %. Left-click → app, right-click → flip label (it learns).
- **App** (`focuslog app` / launcher "focuslog"): dashboard with today vs. goal, focus %, hourly + 7-day charts, top study/waste titles. Served on `127.0.0.1:47615` only.

## Install

```sh
git clone https://github.com/piyush97/focuslog ~/focuslog && cd ~/focuslog && ./install.sh
```

Prompts for your TypeSafe API key (or reads `$TYPESAFE_API_KEY`) → `~/.config/focuslog/env` (mode 600, never in git). Then installs the service, launcher entry, bar plugin (`~/.config/omarchy/plugins/piyush97.focuslog`, enabled at the right of the bar), and `SUPER+CTRL+G` → flip label. Safe to re-run; also removes the old inline bar module.

## Use

```sh
focuslog app           # dashboard window
focuslog report [7]    # terminal report
focuslog mark [study|waste|neutral]   # relabel focused window (no arg = flip)
focuslog classify chromium "Designing Twitter - YouTube"   # test the classifier
journalctl --user -u focuslog -f
```

Config: `~/.config/focuslog/config.toml` (goal, keywords, Jev model/threshold, nudge timing). Data: `~/.local/share/focuslog/focuslog.db`.

Disable bar widget: `omarchy plugin disable piyush97.focuslog`.
