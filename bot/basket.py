"""MVP του Παναθηναϊκού: EuroLeague (API EuroLeague) και Stoiximan GBL (esake.gr). MVP = ο παίκτης μας με το μεγαλύτερο PIR."""
import html as htmllib
import re
from datetime import datetime

import requests

from .config import TZ
from .flashscore import UA

_s = requests.Session()
_s.headers.update({"User-Agent": UA})


def _json(url):
    try:
        r = _s.get(url, timeout=25)
        return r.json() if r.status_code == 200 else None
    except (requests.RequestException, ValueError):
        return None


def _text(url):
    try:
        r = _s.get(url, timeout=25)
        return r.text if r.status_code == 200 else ""
    except requests.RequestException:
        return ""


def _title(s):
    return " ".join(w[:1].upper() + w[1:].lower() for w in s.split())


def is_euroleague(ev):
    return ev["comp"] in ("Ευρωλίγκα", "EuroLeague")


def is_gbl(ev):
    return "GBL" in ev["comp"] or "Basket League" in ev["comp"]


def season_year(ts):
    d = datetime.fromtimestamp(ts, TZ)
    return d.year if d.month >= 8 else d.year - 1


def euroleague_mvp(ev):
    season = f"E{season_year(ev['start'])}"
    games = _json(
        f"https://feeds.incrowdsports.com/provider/euroleague-feeds/v2/competitions/E/seasons/{season}/games?teamCode=PAN&pageSize=100"
    )
    game = None
    for g in (games or {}).get("data", []):
        ts = datetime.fromisoformat(g["date"].replace("Z", "+00:00")).timestamp()
        if abs(ts - ev["start"]) < 4 * 3600:
            game = g
            break
    if not game or game.get("status") != "result":
        return None
    side = "local" if game["home"]["code"] == "PAN" else "road"
    st = _json(f"https://api-live.euroleague.net/v3/competitions/E/seasons/{season}/games/{game['code']}/stats")
    players = ((st or {}).get(side) or {}).get("players") or []
    best = None
    for p in players:
        s = p.get("stats") or {}
        if best is None or (s.get("valuation") or 0) > (best["stats"].get("valuation") or 0):
            best = p
    if not best or not (best["stats"].get("timePlayed") or best["stats"].get("points") is not None):
        return None
    s = best["stats"]
    name = best["player"]["person"]["name"]
    last, _, first = name.partition(",")
    return {
        "first": _title(first.strip()),
        "last": _title(last.strip()),
        "number": best["player"].get("dorsal", ""),
        "photo": (best["player"].get("images") or {}).get("action") or (best["player"].get("images") or {}).get("headshot") or "",
        "stats": [
            (s.get("points", 0), "ΠΟΝΤΟΙ"),
            (s.get("totalRebounds", 0), "ΡΙΜΠΑΟΥΝΤ"),
            (s.get("assistances", 0), "ΑΣΙΣΤ"),
            (s.get("steals", 0), "ΚΛΕΨΙΜΑΤΑ"),
            (s.get("valuation", 0), "PIR"),
        ],
        "pir": s.get("valuation", 0),
        "comp": "EuroLeague",
    }


ESAKE = "https://www.esake.gr/el/action/EsakeResults"
MONTHS = {"Ιαν": 1, "Φεβ": 2, "Μαρ": 3, "Απρ": 4, "Μαΐ": 5, "Μαι": 5, "Ιουν": 6, "Ιουλ": 7, "Αυγ": 8, "Σεπ": 9, "Οκτ": 10, "Νοε": 11, "Δεκ": 12}


def _esake_games(page):
    out = []
    for b in page.split('<div class="esake-program-game">')[1:]:
        rm = re.search(r"<h5>\s*0*(\d+)", b)
        dm = re.search(r"clock\.svg[^>]*>\s*\S+\s+(\d{1,2})\s+(\S+)\s*-\s*(\d{1,2}):(\d{2})", b)
        im = re.search(r"idgame=([0-9A-F]+)", b, re.I)
        if not (rm and dm and im and dm.group(2) in MONTHS):
            continue
        names = [htmllib.unescape(x).strip() for x in re.findall(r"<span>([^<]+)", b)]
        names = [n for n in names if n and n != "-" and "\xa0" not in n]
        out.append({"id": im.group(1).upper(), "round": int(rm.group(1)), "day": int(dm.group(1)), "month": MONTHS[dm.group(2)], "names": names[:2]})
    return out


def gbl_mvp(ev):
    d = datetime.fromtimestamp(ev["start"], TZ)
    page = _text(ESAKE)
    games = _esake_games(page)
    ch = re.search(r'id="idchampionship".*?value="(\w+)"\s+selected', page, re.S)
    se = re.search(r'id="idseason".*?value="(\w+)"\s+selected', page, re.S)
    if games and ch and se:
        rnd = max(g["round"] for g in games)
        for r in (rnd - 1, rnd - 2):
            if r >= 1:
                games += _esake_games(_text(f"{ESAKE}?idchampionship={ch.group(1)}&idteam=&idseason={se.group(1)}&series={r}"))
    game = next(
        (g for g in games if g["day"] == d.day and g["month"] == d.month and any("ΠΑΝΑΘΗΝΑ" in n for n in g["names"])),
        None,
    )
    if not game:
        return None
    ti = 0 if "ΠΑΝΑΘΗΝΑ" in game["names"][0] else 1
    view = _text(f"https://www.esake.gr/el/action/EsakegameView?idgame={game['id']}&mode=3")
    tables = re.findall(r'<table class="table table-esake table-center table-sorter">(.*?)</table>', view, re.S)
    if len(tables) < 2:
        return None
    best = None
    for tr in tables[ti].split("<tr>"):
        nm = re.search(r"<SPAN>([^<]+)</SPAN>\s*([^<]*)</a>", tr)
        if not nm:
            continue
        c = re.findall(r"<td[^>]*>\s*([^<]*?)\s*</td>", tr)
        if len(c) < 16:
            continue

        def n(i):
            v = c[i].strip()
            return int(v) if v.lstrip("-").isdigit() else 0

        p = {
            "first": _title(nm.group(2).strip()),
            "last": _title(nm.group(1).strip()),
            "number": "",
            "photo": "",
            "stats": [(n(0), "ΠΟΝΤΟΙ"), (n(4), "ΡΙΜΠΑΟΥΝΤ"), (n(7), "ΑΣΙΣΤ"), (n(12), "ΚΛΕΨΙΜΑΤΑ"), (n(15), "PIR")],
            "pir": n(15),
            "comp": "Stoiximan GBL",
        }
        if best is None or p["pir"] > best["pir"]:
            best = p
    return best


def mvp(ev):
    if is_euroleague(ev):
        return euroleague_mvp(ev)
    if is_gbl(ev):
        return gbl_mvp(ev)
    return None
