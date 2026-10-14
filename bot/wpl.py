"""Εφεδρική πηγή για το πόλο: το live σύστημα της ΚΟΕ (live.koe.org.gr, Water Polo League).

Το Flashscore δεν καλύπτει ζωντανά την Α1 και περνά το αποτέλεσμα ώρες αργότερα.
Η ΚΟΕ δίνει κατάσταση αγώνα (FINISHED), τελικό σκορ, σκορ ανά περίοδο και πέναλτι.
"""
import re
from datetime import datetime

import requests

from .config import TZ
from .flashscore import UA

API = "https://live.koe.org.gr/api-waterpolo/wp/KOE/get"

_cache = {}


def _get(url):
    if url not in _cache:
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
            _cache[url] = r.json() if r.status_code == 200 else None
        except (requests.RequestException, ValueError):
            _cache[url] = None
    return _cache[url]


def _competition(ts):
    """Ο κωδικός της ΚΟΕ για το «WPL 2026-2027» (Α1 ανδρών) της σεζόν του αγώνα."""
    d = datetime.fromtimestamp(ts, TZ)
    y = d.year if d.month >= 8 else d.year - 1
    name = f"WPL {y}-{y + 1}"
    for e in (_get(f"{API}/events/ASM") or {}).get("Events", []):
        if re.sub(r"\s+", " ", e.get("GaraDescrEng", "")).strip() == name:
            return e["GaraCode"]
    return None


def result(ev, pao_is_home):
    """Τελικό αποτέλεσμα αν ο αγώνας έχει τελειώσει: {home_score, away_score, periods}, με τη σειρά του Flashscore."""
    code = _competition(ev["start"])
    if not code:
        return None
    day = datetime.fromtimestamp(ev["start"], TZ).strftime("%d/%m/%Y")
    sched = (_get(f"{API}/schedulereferee/ASM/{code}/*/*/*") or {}).get("Schedule", [])
    m = next(
        (
            x
            for x in sched
            if x.get("OraMatchDate") == day
            and ("ΠΑΝΑΘΗΝΑ" in (x.get("OraTeamNameA") or "") or "ΠΑΝΑΘΗΝΑ" in (x.get("OraTeamNameB") or ""))
        ),
        None,
    )
    if not m or m.get("ScheduleStatus") != "FINISHED":
        return None
    a, b = int(m.get("OraResA") or 0), int(m.get("OraResB") or 0)
    periods = []
    det = _get(
        f"{API}/resultsDBlikeJSON/ASM/{code}/{m['OraTurCode']}/{m['OraGruCode']}/{m['OraTeamCodeA']}/{m['OraTeamCodeB']}"
    )
    for q in (det or {}).get("q", []):
        if str(q.get("st")) == "2" and str(q.get("r1", "")).isdigit() and str(q.get("r2", "")).isdigit():
            periods.append((int(q["r1"]), int(q["r2"])))
    koe_pao_home = "ΠΑΝΑΘΗΝΑ" in (m.get("OraTeamNameA") or "")
    if koe_pao_home != pao_is_home:
        a, b = b, a
        periods = [(y, x) for x, y in periods]
    return {"home_score": a, "away_score": b, "periods": periods}
