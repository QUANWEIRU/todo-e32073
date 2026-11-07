#!/usr/bin/env python3
"""把 ntfy 上的勾选事件归档进 state.json（GitHub Action 定时执行）"""
import json, os, sys, urllib.request, urllib.error

TOPIC = os.environ.get("NTFY_TOPIC") or json.load(open("config.json", encoding="utf-8"))["topic"]
STATE = "state.json"
SEEN = "state.json"  # 复用同一份（记录 lastTime）

def load():
    try:
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"rev": 0, "items": {}, "lastTime": 0}

def fetch_events():
    url = f"https://ntfy.sh/{TOPIC}/json?poll=1&since=all"
    req = urllib.request.Request(url, headers={"User-Agent": "todo-sync"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode("utf-8", "replace")
    out = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("event") != "message" or not ev.get("message"):
            continue
        try:
            payload = json.loads(ev["message"])
        except Exception:
            continue
        if not payload.get("no") or payload["no"] == "__init__":
            continue
        payload["_ts"] = ev.get("time", 0)
        out.append(payload)
    out.sort(key=lambda p: p.get("_ts", 0))
    return out

def main():
    st = load()
    items = st.setdefault("items", {})
    changed = False
    for ev in fetch_events():
        no = ev["no"]; patch = ev.get("patch") or {}
        cur = items.get(no) or {"done": False, "owner": "待认领", "note": ""}
        new = dict(cur)
        if "done" in patch: new["done"] = bool(patch["done"])
        if "owner" in patch: new["owner"] = patch["owner"] or "待认领"
        if "note" in patch: new["note"] = patch["note"] or ""
        new["by"] = ev.get("by", "")
        new["ts"] = ev.get("_ts", 0)
        if {k: cur.get(k) for k in ("done", "owner", "note")} != {k: new.get(k) for k in ("done", "owner", "note")}:
            items[no] = new; changed = True; st["rev"] = int(st.get("rev", 0)) + 1
    if changed:
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False, indent=1)
        print(f"state updated, rev={st['rev']}, items={len(items)}")
    else:
        print("no change")

if __name__ == "__main__":
    main()
