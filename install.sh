#!/usr/bin/env bash
# Per-user install: no sudo, package downloads, or removal of user data.
set -euo pipefail
D="$(cd "$(dirname "$0")" && pwd)"
BIN="$HOME/.local/bin/focuslog"
CFG="$HOME/.config/focuslog"
PID="piyush97.focuslog"

command -v python3 >/dev/null || { printf 'Python 3.11+ is required.\n' >&2; exit 1; }
python3 -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ is required"'
command -v systemctl >/dev/null || { printf 'A systemd user session is required.\n' >&2; exit 1; }
command -v hyprctl >/dev/null || { printf 'Hyprland is required for activity tracking.\n' >&2; exit 1; }

mkdir -p "$HOME/.local/bin" "$CFG" "$HOME/.config/systemd/user" "$HOME/.local/share/applications"
python3 - "$D" <<'PY'
import json, os, shlex, shutil, sys, tomllib
from pathlib import Path
src = Path(sys.argv[1]).resolve()
home = Path.home()
cfg = home / '.config/focuslog'
app = home / '.local/share/focuslog/app'
plugin = home / '.config/omarchy/plugins/piyush97.focuslog'
app.mkdir(parents=True, exist_ok=True)
config = cfg / 'config.toml'
if not config.exists():
    shutil.copy2(src / 'config.toml', config)
else:
    text = config.read_text()
    existing = tomllib.loads(text)
    if 'jev' not in existing:
        backup = cfg / 'config.toml.before-jev'
        if not backup.exists(): shutil.copy2(config, backup)
        defaults = (src / 'config.toml').read_text().split('[jev]', 1)[1].split('[nudge]', 1)[0]
        config.write_text(text + '\n[jev]' + defaults)
for name in ('focuslog.py', 'app.html'):
    if (src / name).resolve() != (app / name).resolve():
        shutil.copy2(src / name, app / name)
(app / 'focuslog.py').chmod(0o755)
link = home / '.local/bin/focuslog'
if link.exists() and not link.is_symlink():
    raise SystemExit(f'Refusing to replace a non-symlink command: {link}')
link.unlink(missing_ok=True)
link.symlink_to(app / 'focuslog.py')
shutil.copy2(src / 'focuslog.service', home / '.config/systemd/user/focuslog.service')
binarg = '"' + str(link).replace('\\', '\\\\').replace('"', '\\"') + '"'
desktop = (src / 'focuslog.desktop').read_text().replace('@BIN@', binarg)
(home / '.local/share/applications/focuslog.desktop').write_text(desktop)

if shutil.which('omarchy-shell'):
    manifest = json.loads((src / 'manifest.json').read_text())
    if manifest.get('id') != 'piyush97.focuslog':
        raise SystemExit('Unexpected focuslog plugin manifest ID')
    if not plugin.resolve().is_relative_to(home.resolve() / '.config/omarchy/plugins'):
        raise SystemExit('Invalid plugin destination')
    if plugin.exists():
        installed = plugin / 'manifest.json'
        if not installed.is_file() or json.loads(installed.read_text()).get('id') != manifest['id']:
            raise SystemExit(f'Refusing to overwrite an unrelated plugin directory: {plugin}')
    plugin.mkdir(parents=True, exist_ok=True)
    for name in ('manifest.json', 'Widget.qml'):
        if (src / name).resolve() != (plugin / name).resolve():
            shutil.copy2(src / name, plugin / name)
    shell = home / '.config/omarchy/shell.json'
    if shell.exists():
        data = json.loads(shell.read_text())
        layout = data.get('bar', {}).get('layout', {})
        def entry_id(e): return e.get('id') if isinstance(e, dict) else e
        if any(any(entry_id(e) == 'focuslog' for e in items) for items in layout.values()):
            backup = shell.with_suffix('.json.before-focuslog')
            if not backup.exists(): shutil.copy2(shell, backup)
            for section, items in layout.items():
                layout[section] = [e for e in items if entry_id(e) != 'focuslog']
            tmp = shell.with_suffix('.json.focuslog-new')
            tmp.write_text(json.dumps(data, indent=2) + '\n')
            tmp.replace(shell)
    bind = home / '.config/hypr/bindings.lua'
    if bind.exists() and 'Flip focus label' not in bind.read_text():
        with bind.open('a') as out:
            out.write('\n-- focuslog: flip study/waste label for focused window\n')
            out.write('o.bind("SUPER + CTRL + G", "Flip focus label", ' + json.dumps(shlex.quote(str(link)) + ' mark') + ')\n')
PY

# Keep the TypeSafe key in a private file; never put it in argv or logs.
if [ -f "$CFG/env" ]; then chmod 600 "$CFG/env"; fi
if ! grep -qs '^TYPESAFE_API_KEY=.' "$CFG/env"; then
  key="${TYPESAFE_API_KEY:-}"
  if [ -z "$key" ] && [ -t 0 ]; then
    printf 'Jev sends the configured goal and active window title/class to TypeSafe AI.\n'
    read -r -s -p 'TypeSafe API key (Enter for local rules only): ' key || true
    printf '\n'
  fi
  if [ -n "$key" ]; then (umask 077; printf 'TYPESAFE_API_KEY=%s\n' "$key" >"$CFG/env"); fi
  unset key
fi
[ ! -f "$CFG/env" ] || chmod 600 "$CFG/env"

systemctl --user daemon-reload
systemctl --user enable focuslog.service
systemctl --user restart focuslog.service
systemctl --user is-active --quiet focuslog.service

if command -v omarchy-shell >/dev/null; then
  omarchy-plugin-validate "$HOME/.config/omarchy/plugins/$PID"
  omarchy-shell shell rescanPlugins >/dev/null
  found=0
  for _ in $(seq 1 50); do
    if omarchy-plugin-list --json 2>/dev/null | jq -e --arg id "$PID" 'any(.[]; .id == $id)' >/dev/null; then found=1; break; fi
    sleep 0.1
  done
  [ "$found" = 1 ] || { printf 'Omarchy did not discover the focuslog widget.\n' >&2; exit 1; }
  omarchy-plugin-enable "$PID" --section right --index 0
  omarchy-shell shell reloadConfig >/dev/null
else
  printf 'Tracker installed. Add focuslog Waybar JSON output to your Waybar config.\n'
fi
printf 'Installed. Open focuslog from the app launcher or run focuslog app.\n'
