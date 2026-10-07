import json
import os
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.tmp.cleanup)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            self.port = sock.getsockname()[1]
        env = dict(os.environ, FOCUSLOG_PORT=str(self.port), FOCUSLOG_DB=self.tmp.name+'/db', FOCUSLOG_CONFIG=self.tmp.name+'/config.toml')
        self.proc = subprocess.Popen(['python3', str(ROOT/'focuslog.py'), 'serve'], env=env,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        self.addCleanup(self.stop)
        self.url = f'http://127.0.0.1:{self.port}'
        for _ in range(100):
            try:
                with urllib.request.urlopen(self.url, timeout=.2):
                    return
            except (OSError, urllib.error.URLError):
                if self.proc.poll() is not None:
                    self.fail(self.proc.stderr.read().decode())
                time.sleep(.02)
        self.fail('Dashboard did not start')

    def stop(self):
        self.proc.terminate()
        self.proc.wait(timeout=5)
        self.proc.stderr.close()

    def test_dashboard_and_stats(self):
        with urllib.request.urlopen(self.url) as response:
            self.assertIn(b'<title>focuslog</title>', response.read())
            self.assertEqual(response.headers['Cache-Control'], 'no-store')
            self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
            self.assertNotIn('Access-Control-Allow-Origin', response.headers)
        with urllib.request.urlopen(self.url+'/api/stats') as response:
            d = json.load(response)
            self.assertEqual(len(d['week']), 7)
            self.assertEqual(len(d['hours']), 24)

    def test_unrelated_hosts_and_cross_origin_blocked(self):
        for h in ({'Host':'evil.example'}, {'Sec-Fetch-Site':'cross-site'}):
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(urllib.request.Request(self.url+'/api/stats', headers=h))
            self.assertEqual(error.exception.code, 403)

    def test_demo_is_explicit_and_does_not_write_activity(self):
        result = subprocess.run(['python3', str(ROOT/'focuslog.py'), 'demo-stats'],
                                env=dict(os.environ, FOCUSLOG_DB=self.tmp.name+'/demo-must-not-exist.db'),
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertTrue(data['demo'])
        self.assertEqual(len(data['week']), 7)
        self.assertGreater(data['today']['study'], 0)
        self.assertFalse(Path(self.tmp.name+'/demo-must-not-exist.db').exists())

    def test_unknown_paths_are_not_served(self):
        for path in ('/etc/passwd', '/../../etc/passwd', '/api/stats-wrong'):
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(self.url+path)
            self.assertEqual(error.exception.code, 404)


if __name__ == '__main__':
    unittest.main()
