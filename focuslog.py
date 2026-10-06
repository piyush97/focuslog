#!/usr/bin/env python3
"""focuslog - study vs. time-waste tracker for Omarchy/Hyprland."""
import json, os, sqlite3, subprocess, sys, time, tomllib, urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
CFG_PATH = Path(os.environ.get("FOCUSLOG_CONFIG", Path.home() / ".config/focuslog/config.toml"))
DB_PATH = Path(os.environ.get("FOCUSLOG_DB", Path.home() / ".local/share/focuslog/focuslog.db"))
CATS = ("study", "waste", "neutral")


def cfg():
    load_env()
    p = CFG_PATH if CFG_PATH.exists() else HERE / "config.toml"
    return tomllib.loads(p.read_text())


def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.executescript("""
      CREATE TABLE IF NOT EXISTS samples(ts REAL, day TEXT, secs REAL, cat TEXT, cls TEXT, title TEXT);
      CREATE INDEX IF NOT EXISTS samples_day ON samples(day);
      CREATE TABLE IF NOT EXISTS verdicts(key TEXT PRIMARY KEY, cat TEXT, src TEXT);""")
    return c


# ---------- window ----------
def locked():
    """Quattro: shell-native lock via IPC. Older Omarchy: hyprlock process."""
    try:
        r = subprocess.run(["omarchy-shell", "-q", "lock", "isLocked"], capture_output=True, text=True, timeout=3)
        if r.stdout.strip() == "true":
            return True
    except Exception:
        pass
    return subprocess.run(["pgrep", "-x", "hyprlock"], capture_output=True).returncode == 0


def active_window():
    """(class, title) or None when idle/locked."""
    if locked():
        return None
    try:
        w = json.loads(subprocess.run(["hyprctl", "activewindow", "-j"], capture_output=True,
                                      text=True, timeout=3).stdout or "{}")
    except Exception:
        return None
    if not w.get("class"):
        return None
    return w["class"], w.get("title", "")


# ---------- classifier ----------
def _has(text, words):
    t = text.lower()
    return any(w.lower() in t for w in words)


def load_env():
    """TYPESAFE_API_KEY etc. from ~/.config/focuslog/env (systemd + bar don't see shell rc)."""
    p = CFG_PATH.parent / "env"
    if p.exists():
        for line in p.read_text().splitlines():
            k, sep, v = line.strip().partition("=")
            if sep and not k.startswith("#"):
                os.environ.setdefault(k.strip().removeprefix("export "), v.strip().strip("'\""))


def ask_llm(c, cls, title):
    """Jev (TypeSafe AI) Choice question -> study|waste|neutral, or None."""
    j = c.get("jev", {})
    key = os.environ.get("TYPESAFE_API_KEY")
    if not j.get("enabled", True) or not key:
        return None
    body = json.dumps({
        "model": j.get("model", "jev-latest"),
        "state": {"goal": c["goal"], "app": cls, "window_title": title},
        "questions": {"activity": {
            "type": "choice",
            "instructions": "Given `goal`, is the user studying, wasting time, or doing something neutral in this window?",
            "criteria": {
                "study": "directly advances `goal`: learning material, practice problems, notes, coding, technical videos",
                "waste": "entertainment, social media, gaming, unrelated videos, news, shopping",
                "neutral": "system tools, settings, file managers, or genuinely unclear"}}}}).encode()
    req = urllib.request.Request(j.get("url", "https://api.typesafe.ai/v1/systemone"), body,
                                 {"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    try:
        a = json.loads(urllib.request.urlopen(req, timeout=j.get("timeout", 10)).read())["answers"]["activity"]
    except Exception as e:
        print(f"jev error: {e}", file=sys.stderr)
        return None
    if a.get("confidence", 1) < j.get("min_confidence", 0.5):
        return "neutral"
    return a["choice"] if a.get("choice") in CATS else None


def classify(c, conn, cls, title):
    """Return (category, source)."""
    key = f"{cls}\x1f{title}"
    row = conn.execute("SELECT cat, src FROM verdicts WHERE key=?", (key,)).fetchone()
    if row:
        return row
    s, w = c["study"], c["waste"]
    is_browser = _has(cls, c.get("browsers", []))
    if _has(title, s.get("title_keywords", [])):
        v = ("study", "rule")
    elif is_browser and (r := ask_llm(c, cls, title)):
        v = (r, "jev")
    elif _has(title, w.get("title_keywords", [])):
        v = ("waste", "rule")
    elif cls.lower() in map(str.lower, s.get("classes", [])):
        v = ("study", "rule")
    elif cls.lower() in map(str.lower, w.get("classes", [])):
        v = ("waste", "rule")
    elif not is_browser and (r := ask_llm(c, cls, title)):
        v = (r, "jev")
    else:
        v = ("neutral", "default")
    if v[1] != "default":  # cache so Jev is called once per title
        conn.execute("INSERT OR REPLACE INTO verdicts VALUES(?,?,?)", (key, *v))
        conn.commit()
    return v


# ---------- daemon ----------
def notify(msg, urgency="normal"):
    head, _, body = msg.partition("\n")
    for cmd in (["omarchy-notification-send", "--app-name", "focuslog", "-g", "󰑴", "-u", urgency, head, body],
                ["notify-send", "-u", urgency, "-a", "focuslog", head, body]):
        try:
            if subprocess.run(cmd, capture_output=True).returncode == 0:
                return
        except FileNotFoundError:
            pass


def run(interval=5):
    c, conn = cfg(), db()
    n = c.get("nudge", {})
    waste_limit = n.get("waste_minutes", 5) * 60
    goal = c.get("daily_goal_minutes", 120) * 60
    streak, last, goal_hit = 0.0, time.time(), None
    while True:
        time.sleep(interval)
        now = time.time()
        secs, last = min(now - last, interval * 6), now  # cap gaps (suspend)
        w = active_window()
        if w is None:
            streak = 0
            continue
        cat, _ = classify(c, conn, *w)
        today = date.today().isoformat()
        conn.execute("INSERT INTO samples VALUES(?,?,?,?,?,?)", (now, today, secs, cat, *w))
        conn.commit()
        if cat == "waste":
            streak += secs
            if streak >= waste_limit:
                notify(f"{int(streak // 60)} min on: {w[1][:60]}\nBack to studying?", "critical")
                streak = waste_limit - n.get("repeat_minutes", 3) * 60  # nag again later
        elif cat == "study":
            streak = 0
        if goal_hit != today and totals(conn, today)["study"] >= goal:
            goal_hit = today
            notify(f"Daily study goal hit: {fmt(goal)} 🎉")


# ---------- stats / output ----------
def fmt(s):
    s = int(s)
    return f"{s // 3600}h{s % 3600 // 60:02d}m" if s >= 3600 else f"{s // 60}m"


def totals(conn, day):
    t = dict.fromkeys(CATS, 0.0)
    for cat, s in conn.execute("SELECT cat, SUM(secs) FROM samples WHERE day=? GROUP BY cat", (day,)):
        t[cat] = s
    return t


def waybar():
    c, conn = cfg(), db()
    t = totals(conn, date.today().isoformat())
    goal = c.get("daily_goal_minutes", 120) * 60
    pct = min(100, int(100 * t["study"] / goal)) if goal else 0
    focus = t["study"] / (t["study"] + t["waste"]) if t["study"] + t["waste"] else 1
    last = conn.execute("SELECT cat FROM samples ORDER BY ts DESC LIMIT 1").fetchone()
    icon = {"study": "󰑴", "waste": "󰒲"}.get(last and last[0], "󰔛")
    tip = (f"Study  {fmt(t['study'])} / {fmt(goal)} ({pct}%)\nWaste  {fmt(t['waste'])}\n"
           f"Other  {fmt(t['neutral'])}\nFocus  {focus:.0%}\n\nClick: open focuslog app\n"
           f"Right-click: mislabeled? flip focused window")
    print(json.dumps({"text": f"{icon} {fmt(t['study'])} · {fmt(t['waste'])}", "tooltip": tip,
                      "class": "active" if focus < .5 else "study", "percentage": pct}))


def report(days=1):
    conn = db()
    for i in range(days - 1, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        t = totals(conn, d)
        bar = lambda s: "█" * int(s // 600)
        print(f"\n== {d} ==  study {fmt(t['study'])}  waste {fmt(t['waste'])}  other {fmt(t['neutral'])}")
        print(f"  study {bar(t['study'])}\n  waste {bar(t['waste'])}")
        if days == 1:
            for cat in ("study", "waste"):
                rows = conn.execute("SELECT title, cls, SUM(secs) s FROM samples WHERE day=? AND cat=? "
                                    "GROUP BY cls, title ORDER BY s DESC LIMIT 8", (d, cat)).fetchall()
                if rows:
                    print(f"\n  top {cat}:")
                    for title, cls, s in rows:
                        print(f"   {fmt(s):>6}  {(title or cls)[:70]}")


def mark(cat=None):
    """Relabel the current window (teaches the cache). No arg = flip study<->waste."""
    conn, w = db(), active_window()
    if not w:
        return print("no active window")
    key = f"{w[0]}\x1f{w[1]}"
    if cat is None:
        cur, _ = classify(cfg(), conn, *w)
        cat = "waste" if cur == "study" else "study"
    conn.execute("INSERT OR REPLACE INTO verdicts VALUES(?,?,?)", (key, cat, "user"))
    conn.execute("UPDATE samples SET cat=? WHERE day=? AND cls=? AND title=?",
                 (cat, date.today().isoformat(), *w))
    conn.commit()
    notify(f"Marked as {cat}: {w[1][:60]}")


# ---------- desktop app (local dashboard) ----------
PORT = int(os.environ.get("FOCUSLOG_PORT", 47615))


def stats(days=7):
    c, conn = cfg(), db()
    today = date.today().isoformat()
    week = []
    for i in range(days - 1, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        week.append({"day": d, **totals(conn, d)})
    top = {cat: [{"title": t or k, "secs": s} for t, k, s in conn.execute(
        "SELECT title, cls, SUM(secs) s FROM samples WHERE day=? AND cat=? GROUP BY cls, title "
        "ORDER BY s DESC LIMIT 10", (today, cat))] for cat in ("study", "waste")}
    hours = [dict.fromkeys(CATS, 0.0) for _ in range(24)]
    for ts, cat, s in conn.execute("SELECT ts, cat, secs FROM samples WHERE day=?", (today,)):
        hours[datetime.fromtimestamp(ts).hour][cat] += s
    last = conn.execute("SELECT cat, title FROM samples ORDER BY ts DESC LIMIT 1").fetchone()
    return {"today": week[-1], "week": week, "top": top, "hours": hours, "goal": c.get("daily_goal_minutes", 120) * 60,
            "now": {"cat": last[0], "title": last[1]} if last else None,
            "jev": bool(os.environ.get("TYPESAFE_API_KEY")) and c.get("jev", {}).get("enabled", True)}


def serve():
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/api/stats"):
                body, ctype = json.dumps(stats()).encode(), "application/json"
            elif self.path in ("/", "/index.html"):
                body, ctype = (HERE / "app.html").read_bytes(), "text/html; charset=utf-8"
            else:
                return self.send_error(404)
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()


def app():
    """Open the dashboard as a desktop app window (Omarchy web-app style)."""
    import socket
    if socket.socket().connect_ex(("127.0.0.1", PORT)):
        subprocess.Popen([sys.executable, __file__, "serve"], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.6)
    url = f"http://127.0.0.1:{PORT}/"
    for cmd in (["omarchy-launch-webapp", url], ["chromium", f"--app={url}"], ["xdg-open", url]):
        try:
            return subprocess.Popen(cmd, start_new_session=True)
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    a = sys.argv[1:] or ["help"]
    if a[0] == "run":
        run()
    elif a[0] == "waybar":
        waybar()
    elif a[0] == "report":
        report(int(a[1]) if len(a) > 1 else 1)
    elif a[0] == "mark":
        mark(a[1] if len(a) > 1 and a[1] in CATS else None)
    elif a[0] == "serve":
        serve()
    elif a[0] == "app":
        app()
    elif a[0] == "stats":
        print(json.dumps(stats(), indent=1))
    elif a[0] == "classify":
        print(classify(cfg(), db(), a[1], a[2] if len(a) > 2 else ""))
    else:
        print("usage: focuslog run | app | waybar | report [days] | stats | mark [study|waste|neutral] | classify CLASS TITLE")
