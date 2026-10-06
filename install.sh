#!/usr/bin/env bash
# Install focuslog on Omarchy (Hyprland + Waybar)
set -euo pipefail
D="$(cd "$(dirname "$0")" && pwd)"
mkdir -p ~/.local/bin ~/.config/focuslog ~/.config/systemd/user
ln -sf "$D/focuslog.py" ~/.local/bin/focuslog && chmod +x "$D/focuslog.py"
[ -f ~/.config/focuslog/config.toml ] || cp "$D/config.toml" ~/.config/focuslog/
cp "$D/focuslog.service" ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now focuslog

if command -v ollama >/dev/null; then ollama pull llama3.1:8b || true
else echo "!! ollama missing: sudo pacman -S ollama-cuda && systemctl enable --now ollama && ollama pull llama3.1:8b (rules still work without it)"; fi

cat <<'MSG'

Add to ~/.config/waybar/config.jsonc  ("modules-right": [..., "custom/focuslog"]):
  "custom/focuslog": {
    "exec": "focuslog waybar", "return-type": "json", "interval": 10,
    "on-click": "alacritty --class focuslog -e sh -c 'focuslog report; read'",
    "on-click-right": "focuslog mark"
  }
Add to ~/.config/waybar/style.css:
  #custom-focuslog.waste { color: #f7768e; }  #custom-focuslog.study { color: #9ece6a; }
Optional keybind (~/.config/hypr/bindings.conf):
  bindd = SUPER SHIFT, F, Flip focus label, exec, focuslog mark
Then: omarchy-restart-waybar
MSG
