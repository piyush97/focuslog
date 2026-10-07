#!/usr/bin/env bash
# Remove focuslog app/service/UI. Preserve the config, API key, and study history.
set -euo pipefail
systemctl --user disable --now focuslog.service >/dev/null 2>&1 || true
if command -v omarchy-plugin-disable >/dev/null; then
  omarchy-plugin-disable piyush97.focuslog >/dev/null 2>&1 || true
fi
python3 - <<'PY'
import json, shutil
from pathlib import Path
home = Path.home()
for name in ('.config/systemd/user/focuslog.service', '.local/share/applications/focuslog.desktop'):
    (home / name).unlink(missing_ok=True)
link = home / '.local/bin/focuslog'
if link.is_symlink() and Path(link).resolve() == home / '.local/share/focuslog/app/focuslog.py':
    link.unlink()
app = home / '.local/share/focuslog/app'
if app.exists() and app.resolve() == home / '.local/share/focuslog/app':
    shutil.rmtree(app)
shell = home / '.config/omarchy/shell.json'
if shell.exists():
    data = json.loads(shell.read_text())
    def entry_id(e): return e.get('id') if isinstance(e, dict) else e
    for section, items in data.get('bar', {}).get('layout', {}).items():
        data['bar']['layout'][section] = [e for e in items if entry_id(e) not in ('focuslog', 'piyush97.focuslog')]
    tmp = shell.with_suffix('.json.focuslog-new')
    tmp.write_text(json.dumps(data, indent=2) + '\n')
    tmp.replace(shell)
bind = home / '.config/hypr/bindings.lua'
if bind.exists():
    lines = [line for line in bind.read_text().splitlines(True)
             if not (line.startswith('-- focuslog:') or ('Flip focus label' in line and 'focuslog' in line))]
    bind.write_text(''.join(lines))
plugin = home / '.config/omarchy/plugins/piyush97.focuslog'
# Keep marketplace-managed Git checkouts so `omarchy plugin remove` can manage them.
if plugin.exists() and not (plugin / '.git').exists():
    manifest = plugin / 'manifest.json'
    if manifest.is_file() and json.loads(manifest.read_text()).get('id') == 'piyush97.focuslog':
        shutil.rmtree(plugin)
PY
systemctl --user daemon-reload
if command -v omarchy-shell >/dev/null; then
  omarchy-shell -q shell rescanPlugins >/dev/null
  omarchy-shell -q shell reloadConfig >/dev/null
fi
printf 'Removed focuslog app/service/widget placement. Database, config and API key are unchanged.\n'
