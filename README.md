# focuslog

Study-vs-time-waste tracker for [Omarchy](https://omarchy.org) (Hyprland + Waybar).

- Every 5 s it checks the active window (`hyprctl activewindow -j`). Locked screen = not counted.
- **Classifier:** your keyword lists first (instant), then a local LLM via Ollama for anything ambiguous, e.g. YouTube titles. Each title is classified once and cached.
- **Nudge:** after 5 min of continuous waste → critical notification, repeated every 3 min until you go back.
- **Waybar:** `󰑴 1h20m · 14m` (study · waste), red when focus < 50 %. Hover = breakdown; click = today's report; right-click = flip the label of the current window (it learns).

## Install

```sh
sudo pacman -S ollama-cuda && sudo systemctl enable --now ollama   # NVIDIA GPU
git clone https://github.com/piyush97/focuslog && cd focuslog && ./install.sh
```
Paste the Waybar snippet it prints, then `omarchy-restart-waybar`.

## Use

```sh
focuslog report        # today + top study/waste titles
focuslog report 7      # last 7 days
focuslog mark          # flip current window study<->waste
focuslog mark neutral  # or set explicitly
journalctl --user -u focuslog -f
```

Config: `~/.config/focuslog/config.toml` (goal, keywords, model, nudge timings). Data: `~/.local/share/focuslog/focuslog.db`.
