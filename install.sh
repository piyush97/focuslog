#!/usr/bin/env bash
# Install focuslog on Omarchy: tracker service + desktop app + Quattro bar plugin
set -euo pipefail
D="$(cd "$(dirname "$0")" && pwd)"
BIN="$HOME/.local/bin/focuslog"
CFG="$HOME/.config/focuslog"
PID="piyush97.focuslog"

# 1. CLI + config + Jev key file (0600, never committed)
mkdir -p ~/.local/bin "$CFG" ~/.config/systemd/user ~/.local/share/applications
chmod +x "$D/focuslog.py" && ln -sf "$D/focuslog.py" "$BIN"
[ -f "$CFG/config.toml" ] || cp "$D/config.toml" "$CFG/"
if ! grep -qs '^TYPESAFE_API_KEY=.' "$CFG/env"; then
  if [ -n "${TYPESAFE_API_KEY:-}" ]; then
    (umask 077; echo "TYPESAFE_API_KEY=$TYPESAFE_API_KEY" >"$CFG/env")
  elif [ -t 0 ]; then
    read -rsp "TypeSafe API key (Enter to skip, rules-only): " k; echo
    [ -n "$k" ] && (umask 077; echo "TYPESAFE_API_KEY=$k" >"$CFG/env")
  fi
fi
chmod 600 "$CFG/env" 2>/dev/null || true

# 2. Background tracker
cp "$D/focuslog.service" ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now focuslog
systemctl --user restart focuslog

# 3. Desktop app (launcher entry: "focuslog")
sed "s|@BIN@|$BIN|" "$D/focuslog.desktop" >~/.local/share/applications/focuslog.desktop

# 4. Bar: native Quattro plugin, else Waybar instructions
if command -v omarchy-shell >/dev/null; then
  P=~/.config/omarchy/plugins/$PID
  rm -rf "$P" && mkdir -p "$P" && cp "$D"/omarchy-plugin/* "$P/"
  omarchy-plugin-validate "$P"
  # drop the inline module from earlier versions
  source omarchy-shell-config
  commit "$NORMALIZE | .bar.layout |= map_values(map(select(.id != \"focuslog\")))"
  omarchy-shell -q shell rescanPlugins; sleep 1
  omarchy-plugin-enable "$PID" --section right --index 0 || omarchy-plugin-enable "$PID"

  B=~/.config/hypr/bindings.lua
  if [ -f "$B" ] && ! grep -q "focuslog mark" "$B"; then
    printf '\n-- focuslog: flip study/waste label for focused window\no.bind("SUPER + CTRL + G", "Flip focus label", "%s mark")\n' "$BIN" >>"$B"
  fi
  echo "Done: bar widget enabled, SUPER+CTRL+G flips labels, launcher entry 'focuslog' opens the app."
else
  cat <<MSG
Waybar (pre-Quattro): add "custom/focuslog" to modules-right in ~/.config/waybar/config.jsonc:
  "custom/focuslog": { "exec": "$BIN waybar", "return-type": "json", "interval": 10,
    "on-click": "$BIN app", "on-click-right": "$BIN mark" }
then: omarchy-restart-waybar
MSG
fi
