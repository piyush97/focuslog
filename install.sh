#!/usr/bin/env bash
# Install focuslog on Omarchy (Quattro: Quickshell bar; older: Waybar)
set -euo pipefail
D="$(cd "$(dirname "$0")" && pwd)"
BIN="$HOME/.local/bin/focuslog"

mkdir -p ~/.local/bin ~/.config/focuslog ~/.config/systemd/user
chmod +x "$D/focuslog.py" && ln -sf "$D/focuslog.py" "$BIN"
[ -f ~/.config/focuslog/config.toml ] || cp "$D/config.toml" ~/.config/focuslog/
cp "$D/focuslog.service" ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now focuslog

# Local LLM (RTX = CUDA build)
if ! command -v ollama >/dev/null; then
  sudo pacman -S --needed --noconfirm ollama-cuda && sudo systemctl enable --now ollama
fi
ollama pull "$(sed -n 's/^model *= *"\(.*\)".*/\1/p' ~/.config/focuslog/config.toml)" || echo "!! model pull failed; rules still work"

if command -v omarchy-shell >/dev/null; then
  # Quattro: inline command module in ~/.config/omarchy/shell.json (right section, first)
  source omarchy-shell-config
  commit "$NORMALIZE | .bar.layout.right |= ([\$m] + map(select(.id != \"focuslog\")))" --argjson m "$(jq -n --arg b "$BIN" '{
    id: "focuslog", type: "command", exec: "\($b) waybar", interval: 10,
    onClick: "omarchy-launch-floating-terminal-with-presentation \($b) report",
    onRightClick: "\($b) mark"}')"
  echo "Bar: focuslog added (shell reloaded)."

  # Keybind: SUPER+CTRL+G flips the label of the focused window
  B=~/.config/hypr/bindings.lua
  if [ -f "$B" ] && ! grep -q "focuslog mark" "$B"; then
    printf '\n-- focuslog: flip study/waste label for focused window\no.bind("SUPER + CTRL + G", "Flip focus label", "%s mark")\n' "$BIN" >>"$B"
    echo "Keybind: SUPER+CTRL+G -> focuslog mark"
  fi
else
  cat <<MSG
Waybar (pre-Quattro): add "custom/focuslog" to modules-right in ~/.config/waybar/config.jsonc:
  "custom/focuslog": { "exec": "$BIN waybar", "return-type": "json", "interval": 10,
    "on-click": "alacritty -e sh -c '$BIN report; read'", "on-click-right": "$BIN mark" }
then: omarchy-restart-waybar
MSG
fi
