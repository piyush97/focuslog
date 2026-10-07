import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class InstallTests(unittest.TestCase):
    def test_install_upgrade_uninstall_preserve_data_and_config(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as td:
            home = Path(td) / 'home space'
            bin_dir = Path(td) / 'stubs'
            bin_dir.mkdir()
            home.mkdir()
            stub = '#!/bin/sh\nexit 0\n'
            for cmd in ('hyprctl', 'systemctl', 'omarchy-shell', 'omarchy-plugin-enable', 'omarchy-plugin-validate', 'omarchy-plugin-disable', 'omarchy-plugin-list'):
                p = bin_dir / cmd
                if cmd == 'omarchy-plugin-list':
                    p.write_text("#!/bin/sh\nsleep 0.1\nprintf '%s\\n' '[{\"id\":\"piyush97.focuslog\"}]'\n")
                elif cmd == 'omarchy-plugin-enable':
                    p.write_text("#!/bin/sh\ntest -f \"$HOME/.config/omarchy/plugins/piyush97.focuslog/Widget.qml\"\n")
                else:
                    p.write_text(stub)
                p.chmod(0o755)
            cfg = home / '.config/focuslog'
            cfg.mkdir(parents=True)
            (cfg / 'config.toml').write_text('goal="Learn Rust"\ndaily_goal_minutes=45\n[study]\nclasses=["myeditor"]\n[llm]\nmodel="old"\n')
            (cfg / 'env').write_text('TYPESAFE_API_KEY=not-a-real-key\n')
            shell = home / '.config/omarchy/shell.json'
            shell.parent.mkdir(parents=True)
            original = {'version': 1, 'bar': {'layout': {'left': ['omarchy.menu'], 'center': [], 'right': [{'id':'focuslog'}, 'omarchy.tray']}}, 'plugins':[{'id':'keep-me'}]}
            shell.write_text(json.dumps(original))
            bind = home / '.config/hypr/bindings.lua'
            bind.parent.mkdir(parents=True)
            bind.write_text('-- personal binding\n')
            data = home / '.local/share/focuslog/focuslog.db'
            data.parent.mkdir(parents=True)
            data.write_text('DO NOT DELETE USER DATA')
            env = dict(os.environ, HOME=str(home), PATH=str(bin_dir)+os.pathsep+os.environ['PATH'])
            env.pop('TYPESAFE_API_KEY', None)
            env.pop('JEV_API_KEY', None)
            for _ in range(2):
                r = subprocess.run(['bash', str(ROOT/'install.sh')], env=env, capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stdout+r.stderr)
            self.assertTrue((home/'.local/share/focuslog/app/app.html').is_file())
            self.assertTrue((home/'.local/share/applications/focuslog.desktop').is_file())
            installed = home/'.config/omarchy/plugins/piyush97.focuslog'
            self.assertTrue((installed/'manifest.json').is_file())
            self.assertTrue((installed/'Widget.qml').is_file())
            text = (cfg/'config.toml').read_text()
            self.assertIn('Learn Rust', text)
            self.assertIn('myeditor', text)
            self.assertIn('[jev]', text)
            self.assertEqual((cfg/'env').stat().st_mode & 0o777, 0o600)
            self.assertNotIn('not-a-real-key', (home/'.local/share/applications/focuslog.desktop').read_text())
            self.assertEqual(bind.read_text().count('Flip focus label'), 1)
            self.assertNotIn({'id':'focuslog'}, json.loads(shell.read_text())['bar']['layout']['right'])
            self.assertEqual(json.loads(shell.read_text())['bar']['layout']['left'], ['omarchy.menu'])
            self.assertEqual(json.loads(shell.read_text())['bar']['layout']['right'], ['omarchy.tray'])
            for _ in range(2):
                r = subprocess.run(['bash', str(ROOT/'uninstall.sh')], env=env, capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stdout+r.stderr)
            self.assertEqual(data.read_text(), 'DO NOT DELETE USER DATA')
            self.assertTrue((cfg/'env').is_file())
            self.assertFalse((home/'.local/share/focuslog/app').exists())
            self.assertIn('personal binding', bind.read_text())
            self.assertEqual(json.loads(shell.read_text())['plugins'], [{'id':'keep-me'}])
            shell.write_text(json.dumps({'version': 1, 'bar': {'layout': {'left': ['omarchy.menu'], 'center': [], 'right': ['piyush97.focuslog', 'omarchy.tray']}}, 'plugins': []}))
            r = subprocess.run(['bash', str(ROOT/'uninstall.sh')], env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout+r.stderr)
            self.assertEqual(json.loads(shell.read_text())['bar']['layout']['left'], ['omarchy.menu'])
            self.assertEqual(json.loads(shell.read_text())['bar']['layout']['right'], ['omarchy.tray'])

    def test_plugin_discovery_waits_for_live_shell(self):
        script = (ROOT/'install.sh').read_text()
        self.assertIn('omarchy-plugin-list --json', script)
        self.assertNotIn('omarchy-plugin-catalog', script)

    def test_root_marketplace_manifest(self):
        m = json.loads((ROOT/'manifest.json').read_text())
        self.assertEqual(m['id'], 'piyush97.focuslog')
        self.assertEqual(m['version'], '1.1.0')
        self.assertTrue((ROOT/m['entryPoints']['barWidget']).is_file())
        self.assertEqual(m['entryPoints']['barWidget'], 'Widget.qml')
        self.assertIn('uninstall', (ROOT/'README.md').read_text().lower())


if __name__ == '__main__':
    unittest.main()
