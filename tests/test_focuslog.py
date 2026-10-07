import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('focuslog', ROOT / 'focuslog.py')
assert spec is not None and spec.loader is not None
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)


class TrackerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {}, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        os.environ.pop('TYPESAFE_API_KEY', None)
        self.paths = patch.multiple(f, CFG_PATH=self.path / 'config.toml', DB_PATH=self.path / 'data.db')
        self.paths.start()
        self.addCleanup(self.paths.stop)
        self.c = f.cfg()
        self.conn = f.db()
        self.addCleanup(self.conn.close)

    def answer(self, choice='study', confidence=.9):
        return {'answers': {'activity': {'type': 'choice', 'choice': choice,
                'confidence': confidence, 'probabilities': {'study': .9, 'waste': .05, 'neutral': .05}}}}

    def test_known_site_is_local(self):
        with patch.object(f, 'ask_jev') as api:
            self.assertEqual(f.classify(self.c, self.conn, 'helium', 'HelloInterview'), ('study', 'rule'))
            api.assert_not_called()

    def test_user_override_is_kept(self):
        self.conn.execute('INSERT INTO verdicts VALUES(?,?,?)', ('helium\x1fVideo', 'waste', 'user'))
        self.conn.commit()
        self.assertEqual(f.classify(self.c, self.conn, 'helium', 'Video'), ('waste', 'user'))

    def test_helium_uses_jev_before_waste_keyword(self):
        with patch.object(f, 'ask_jev', return_value='study') as api:
            self.assertEqual(f.classify(self.c, self.conn, 'helium', 'Designing Twitter - YouTube'), ('study', 'jev'))
            api.assert_called_once()

    def test_cache_invalidates_when_goal_changes(self):
        with patch.object(f, 'ask_jev', side_effect=['study', 'waste']) as api:
            self.assertEqual(f.classify(self.c, self.conn, 'chromium', 'Video')[0], 'study')
            c2 = dict(self.c, goal='Learn cooking')
            self.assertEqual(f.classify(c2, self.conn, 'chromium', 'Video')[0], 'waste')
            self.assertEqual(api.call_count, 2)

    def test_api_failure_backoff_limits_repeated_attempts(self):
        with patch.object(f, 'ask_jev', return_value=None) as api:
            for _ in range(5):
                self.assertEqual(f.classify(self.c, self.conn, 'chromium', 'Unknown')[0], 'neutral')
            api.assert_called_once()
            with patch.object(f.time, 'time', return_value=f.time.time()+301):
                f.classify(self.c, self.conn, 'chromium', 'Unknown')
            self.assertEqual(api.call_count, 2)

    def test_low_confidence_is_neutral(self):
        os.environ['TYPESAFE_API_KEY'] = 'unit-test-only'
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = json.dumps(self.answer(confidence=.1)).encode()
        with patch('urllib.request.OpenerDirector.open', return_value=response):
            self.assertEqual(f.ask_jev(self.c, 'chromium', 'Unclear'), 'neutral')

    def test_invalid_answer_is_rejected(self):
        os.environ['TYPESAFE_API_KEY'] = 'unit-test-only'
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = b'{"answers":{"activity":{"choice":"study","confidence":"high"}}}'
        with patch('urllib.request.OpenerDirector.open', return_value=response):
            self.assertIsNone(f.ask_jev(self.c, 'chromium', 'Unknown'))

    def test_plain_http_cannot_receive_key(self):
        os.environ['TYPESAFE_API_KEY'] = 'unit-test-only'
        self.c['jev']['url'] = 'http://example.com/api'
        with patch('urllib.request.OpenerDirector.open') as api:
            self.assertIsNone(f.ask_jev(self.c, 'chromium', 'Unknown'))
            api.assert_not_called()

    def test_prompt_request_has_typed_question(self):
        os.environ['TYPESAFE_API_KEY'] = 'unit-test-only'
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = json.dumps(self.answer()).encode()
        with patch('urllib.request.OpenerDirector.open', return_value=response) as api:
            self.assertEqual(f.ask_jev(self.c, 'helium', 'Designing Twitter'), 'study')
            payload = json.loads(api.call_args.args[0].data)
            self.assertEqual(payload['questions']['activity']['type'], 'choice')
            self.assertEqual(set(payload['questions']['activity']['criteria']), set(f.CATS))
            self.assertEqual(payload['state']['window_title'], 'Designing Twitter')

    def test_mark_invalid_does_not_modify_db(self):
        with patch.object(f, 'active_window', return_value=('kitty', 'shell')), self.assertRaises(ValueError):
            f.mark('invalid')
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM verdicts').fetchone()[0], 0)

    def test_lock_check(self):
        with patch.object(f.subprocess, 'run', return_value=Mock(stdout='true', returncode=0)):
            self.assertIsNone(f.active_window())

    def test_native_lock_query_does_not_suppress_answer(self):
        calls = []
        def run(cmd, **kwargs):
            calls.append(cmd)
            if cmd[0] == 'omarchy-shell':
                return Mock(stdout='true\n', returncode=0) if '-q' not in cmd else Mock(stdout='', returncode=0)
            return Mock(stdout='', returncode=1)
        with patch.object(f.subprocess, 'run', side_effect=run):
            self.assertTrue(f.locked())
        self.assertNotIn('-q', calls[0])

    def test_totals(self):
        self.conn.executemany('INSERT INTO samples VALUES(?,?,?,?,?,?)',
                             [(1, '2026-01-01', 60, 'study', 'browser', 'a'),
                              (2, '2026-01-01', 30, 'waste', 'browser', 'b')])
        self.conn.commit()
        self.assertEqual(f.totals(self.conn, '2026-01-01'), {'study': 60, 'waste': 30, 'neutral': 0})

    def test_private_db(self):
        self.assertEqual(f.DB_PATH.stat().st_mode & 0o777, 0o600)

    def test_stats_shapes(self):
        s = f.stats()
        self.assertEqual(len(s['week']), 7)
        self.assertEqual(len(s['hours']), 24)
        self.assertFalse(s['jev'])

    def test_notification_failure_is_nonfatal(self):
        with patch.object(f.subprocess, 'run', side_effect=FileNotFoundError):
            f.notify('test')


class DashboardTests(unittest.TestCase):
    def test_focus_card_and_mobile_layout(self):
        html = (ROOT / 'app.html').read_text()
        script = html.split('<script>')[1].split('</script>')[0]
        harness = '''
const nodes = {};
for (const id of ['study','waste','focus-score','goal','goalbar','jev','now','hours','hlbl','week','wlbl','tstudy','twaste'])
  nodes[id] = {textContent:'', innerHTML:'', style:{}};
global.document = {getElementById:id=>nodes[id]};
for (const id in nodes) if(id!=='focus') global[id]=nodes[id];
global.focus = function focus() {};
global.setInterval=()=>{};
const z={study:0,waste:0,neutral:0};
global.fetch=async()=>({ok:true,json:async()=>({today:{study:60,waste:60},goal:0,jev:false,now:null,week:[{day:'2026-01-01',...z}],hours:[z],top:{study:[{title:'<img onerror=alert(1)>',secs:1}],waste:[]}})});
'''
        check = '''
setTimeout(()=>{
if(nodes['focus-score'].textContent !== '50%') throw Error('focus percentage: '+nodes['focus-score'].textContent);
if(nodes.goal.textContent.includes('NaN')||nodes.goalbar.style.width.includes('NaN')) throw Error('zero goal');
if(nodes.tstudy.innerHTML.includes('<img')) throw Error('unsafe title HTML');
console.log('DOM regression checks passed');
},20);
'''
        result = subprocess.run(['node', '-e', harness + script + check], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('@media', html)


if __name__ == '__main__':
    unittest.main()
