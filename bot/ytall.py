"""Όλες οι εκπομπές (lives) του καναλιού @trifillakia_gr για τη σελίδα «YouTube» του trifillakia.gr.

docs/youtube.json = {"updated": ts, "videos": [{"id", "title", "ts"}]} (νεότερες πρώτες).
Η αρχική λίστα (594 lives έως 13/11/2026) φτιάχτηκε μία φορά με yt-dlp --flat-playlist στο /streams.
Από εκεί και πέρα κάθε κύκλος του bot προσθέτει όσες νέες βγάζει η ροή RSS των lives (UULV),
μόνο αφού ξεκινήσουν (όχι προγραμματισμένες, 0 προβολές).
Το site (block 41, ytall.js) φτιάχνει από αυτό το πλέγμα με φίλτρα ανά εκπομπή και player.
"""
import html
import json
import os
import re
import time
from datetime import datetime

import requests

from . import youtube

# Εκπομπή από τον τίτλο για τις νέες (οι παλιές έχουν "shows" από τις λίστες αναπαραγωγής του καναλιού, 13/11).
SHOW_RE = [
    ("Roi MAT Show", r"ROI\s*MAT"), ("Pitch Talk", r"PITCH\s*TALK"), ("Green Voice", r"GREEN\s*VOICE"),
    ("PAO INSIDE", r"PAO\s*INSIDE"), ("PAO Playbook", r"PLAYBOOK"), ("EuroLeague Green Zone", r"GREEN\s*ZONE"),
    ("PAO Unfiltered", r"UNFILTERED"), ("13 SHADES OF GREEN", r"13\s*SHADES"), ("Trifylli Talk", r"TRIFYLLI\s*TALK"),
    ("PAO European Pulse", r"EUROPEAN\s*PULSE"), ("2 AND A HALF STEPS", r"HALF\s*STEPS"), ("The Green Room", r"GREEN\s*ROOM"),
    ("The Green View", r"GREEN\s*VIEW"), ("Pap Green Show", r"PAP\s*GREEN"), ("Trifillakia Sports Live", r"SPORTS\s*LIVE"),
    ("PAO Legends", r"PAO\s*LEGENDS"),
]


def shows_of(title):
    return [n for n, rx in SHOW_RE if re.search(rx, title, re.I)][:1]


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "youtube.json")


def update(log=print):
    try:
        with open(OUT, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return False
    vids = data.get("videos", [])
    have = {v["id"] for v in vids}
    r = requests.get(youtube.FEED, params={"nc": int(time.time())}, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    if r.status_code != 200:
        return False
    new = []
    for e in re.findall(r"<entry>(.*?)</entry>", r.text, re.S):
        vid = re.search(r"<yt:videoId>(.*?)</yt:videoId>", e)
        title = re.search(r"<title>(.*?)</title>", e, re.S)
        pub = re.search(r"<published>(.*?)</published>", e)
        views = re.search(r'<media:statistics views="(\d+)"', e)
        if not vid or vid.group(1) in have or not title or (views and views.group(1) == "0"):
            continue
        ts = int(datetime.fromisoformat(pub.group(1).replace("Z", "+00:00")).timestamp()) if pub else int(time.time())
        t = html.unescape(title.group(1)).strip()
        item = {"id": vid.group(1), "title": t, "ts": ts}
        if shows_of(t):
            item["shows"] = shows_of(t)
        new.append(item)
    if not new:
        return False
    data["videos"] = sorted(new, key=lambda v: -v["ts"]) + vids
    data["updated"] = int(time.time())
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
    log("YouTube σελίδα: νέες εκπομπές", [v["title"][:40] for v in new])
    return True
