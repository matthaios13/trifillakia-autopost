"""docs/trending.json για τη μπάρα «🔥 Δημοφιλή» κάτω από το «Έσκασαν μόλις» του trifillakia.gr (block 41, topbar.js).

Παίρνει το πλέγμα «Δημοφιλή της εβδομάδας» (views 4970fcfe) από Ποδόσφαιρο, Μπάσκετ και Ερασιτέχνη
και τα ανακατεύει (1ο ποδόσφαιρο, 1ο μπάσκετ, 1ο ερασιτέχνης, 2ο ...). Ανανεώνεται το πολύ κάθε 30 λεπτά.
"""
import html
import json
import os
import re
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "trending.json")
CATS = ("podosfairo", "mpasket", "erasitehnis")
BLOCK = "4970fcfe"
EVERY = 30 * 60
UA = "Mozilla/5.0 (compatible; TrifillakiaBot/1.0)"


def _items(cat):
    r = requests.get(f"https://www.trifillakia.gr/{cat}", headers={"User-Agent": UA}, timeout=30)
    if r.status_code != 200:
        return []
    h = r.text
    i = h.find(BLOCK)
    if i < 0:
        return []
    seg = h[i:i + 30000]
    out, seen = [], set()
    for url, title in re.findall(r'<a href="(https://www\.trifillakia\.gr/[^"]+/\d+/[^"]+)" title="([^"]+)" rel="bookmark"', seg):
        if url in seen:
            continue
        seen.add(url)
        out.append({"title": html.unescape(title).strip(), "url": url.replace("https://www.trifillakia.gr", ""), "cat": cat})
    return out


def write(log=print):
    try:
        with open(OUT, encoding="utf-8") as fh:
            old = json.load(fh)
    except (OSError, ValueError):
        old = {}
    if time.time() - old.get("checked", 0) < EVERY:
        return
    lists = []
    for c in CATS:
        try:
            lists.append(_items(c))
        except requests.RequestException as e:
            log("trending: σφάλμα", c, repr(e)[:120])
            lists.append([])
    items, seen = [], set()
    for k in range(6):
        for lst in lists:
            if k < len(lst) and lst[k]["url"] not in seen:
                seen.add(lst[k]["url"])
                items.append(lst[k])
    if not items:
        return
    data = {"checked": int(time.time()), "items": items[:8]}
    if data["items"] == old.get("items") and old:
        data["updated"] = old.get("updated", data["checked"])
    else:
        data["updated"] = data["checked"]
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
