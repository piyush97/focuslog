# focuslog

Study-vs-time-waste tracker for [Omarchy](https://omarchy.org) Quattro (Hyprland + Quickshell bar). Falls back to Waybar on older Omarchy.

- Every 5 s it checks the active window (`hyprctl activewindow -j`). Locked screen (Quattro shell lock or hyprlock) = not counted.
- **Classifier:** your keyword lists first (instant), then a local LLM via Ollama for anything ambiguous, e.g. YouTube titles. Each title is classified once and cached.
- **Nudge:** after 5 min of continuous waste → critical notification, repeated every 3 min until you go back.
- **Bar:** `󰑴 1h20m · 14m` (study · waste), urgent color when focus < 50 %. Hover = breakdown; click = today's report; right-click = flip the label of the current window (it learns).

## Install

```sh
git clone https://github.com/piyush97/focuslog ~/focuslog && cd ~/focuslog && ./install.sh
```
Installs `ollama-cuda` if missing, pulls the model, starts the `focuslog` user service, adds the widget to the right of the bar (`~/.config/omarchy/shell.json`, live reload), and binds `SUPER+CTRL+G` → `focuslog mark` in `~/.config/hypr/bindings.lua`. Safe to re-run.

Remove widget: `jq '.bar.layout.right |= map(select(.id != "focuslog"))' ~/.config/omarchy/shell.json > /tmp/s && mv /tmp/s ~/.config/omarchy/shell.json && omarchy-shell shell reloadConfig`

## Use

```sh
focuslog report        # today + top study/waste titles
focuslog report 7      # last 7 days
focuslog mark          # flip focused window study<->waste (SUPER+CTRL+G)
focuslog mark neutral  # or set explicitly
journalctl --user -u focuslog -f
```

Config: `~/.config/focuslog/config.toml` (goal, keywords, model, nudge timings). Data: `~/.local/share/focuslog/focuslog.db`.
