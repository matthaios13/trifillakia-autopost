"""docs/radio.json για τη σελίδα «Radio» του trifillakia.gr (block 41 /* radio */).

Παίρνει το πρόγραμμα του PAO Radio όπως το δείχνει το paoradio.gr (window.PR_SCHEDULE):
[[αρχή, τέλος, εκπομπή, θέμα, είδος (music|rerun|live), βίντεο YouTube], ...]. Ανανεώνεται το πολύ κάθε 10 λεπτά.
"""
import json
import os
import re
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "radio.json")
EVERY = 10 * 60
UA = "Mozilla/5.0 (compatible; TrifillakiaBot/1.0)"


def write(log=print, force=False):
    if not force and os.path.exists(OUT) and time.time() - os.path.getmtime(OUT) < EVERY:
        return
    r = requests.get("https://paoradio.gr/", headers={"User-Agent": UA}, timeout=30)
    m = re.search(r"window\.PR_SCHEDULE = (\[.*?\]);</script>", r.text, re.S)
    rows = json.loads(m.group(1)) if m else []
    rows = [x for x in rows if isinstance(x, list) and len(x) >= 6]
    if not rows:
        log("radio.json: κενό πρόγραμμα, κρατάω το παλιό")
        return
    data = {"updated": int(time.time()), "stream": "https://s32.radiolize.com:8010/radio.mp3",
            "status": "https://s32.radiolize.com:8010/status-json.xsl", "rows": rows}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
    log("radio.json:", len(rows), "γραμμές")


if __name__ == "__main__":
    write(force=True)
