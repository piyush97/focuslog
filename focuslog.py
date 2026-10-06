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
def active_window():
    """(class, title) or None when idle/locked."""
    if subprocess.run(["pgrep", "-x", "hyprlock"], capture_output=True).returncode == 0:
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


def ask_llm(c, cls, title):
    l = c.get("llm", {})
    if not l.get("enabled"):
        return None
    prompt = (f"The user's goal: {c['goal']}\n"
              f"Active window app: {cls}\nWindow title: {title}\n"
              "Is the user STUDYING toward that goal, WASTING time (entertainment, social media, "
              "unrelated videos/news/shopping), or NEUTRAL (system/utility/unclear)? "
              "Answer with exactly one word: study, waste, or neutral.")
    body = json.dumps({"model": l["model"], "prompt": prompt, "stream": False,
                       "options": {"temperature": 0}}).encode()
    try:
        req = urllib.request.Request(l["url"], body, {"Content-Type": "application/json"})
        ans = json.loads(urllib.request.urlopen(req, timeout=l.get("timeout", 15)).read())["response"]
    except Exception as e:
        print(f"llm error: {e}", file=sys.stderr)
        return None
    ans = ans.strip().lower()
    return next((k for k in CATS if k in ans), None)


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
        v = (r, "llm")
    elif _has(title, w.get("title_keywords", [])):
        v = ("waste", "rule")
    elif cls.lower() in map(str.lower, s.get("classes", [])):
        v = ("study", "rule")
    elif cls.lower() in map(str.lower, w.get("classes", [])):
        v = ("waste", "rule")
    elif (r := ask_llm(c, cls, title)) and not is_browser:
        v = (r, "llm")
    else:
        v = ("neutral", "default")
    if v[1] != "default":  # cache rules + llm so the LLM runs once per title
        conn.execute("INSERT OR REPLACE INTO verdicts VALUES(?,?,?)", (key, *v))
        conn.commit()
    return v


# ---------- daemon ----------
def notify(msg, urgency="normal"):
    subprocess.run(["notify-send", "-u", urgency, "-a", "focuslog", "focuslog", msg])


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
           f"Other  {fmt(t['neutral'])}\nFocus  {focus:.0%}\n\nClick: today's report\n"
           f"Right-click: mislabeled? flip current window")
    print(json.dumps({"text": f"{icon} {fmt(t['study'])} · {fmt(t['waste'])}", "tooltip": tip,
                      "class": "waste" if focus < .5 else "study", "percentage": pct}))


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
    elif a[0] == "classify":
        print(classify(cfg(), db(), a[1], a[2] if len(a) > 2 else ""))
    else:
        print("usage: focuslog run | waybar | report [days] | mark [study|waste|neutral] | classify CLASS TITLE")
