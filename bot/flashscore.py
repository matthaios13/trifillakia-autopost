"""Δεδομένα από το Flashscore (ελληνική έκδοση): πρόγραμμα, αποτελέσματα, λεπτομέρειες, βαθμολογίες."""
import json
import re
import time

import requests

BASE = "https://www.flashscore.gr"
IMG = "https://static.flashscore.com/res/image/data/"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)
FSIGN = "SW9D1eZo"

_session = requests.Session()
_session.headers.update({"User-Agent": UA, "Accept-Language": "el-GR,el;q=0.9"})
_cache = {}

# Κωδικοί κατάστασης αγώνα (AC) που σημαίνουν «δεν παίχτηκε κανονικά».
OFF_STATES = {"4", "5", "9", "36", "37", "43", "54"}


def get(url, feed=False):
    if url in _cache:
        return _cache[url]
    headers = {"x-fsign": FSIGN} if feed else {}
    for attempt in range(3):
        try:
            r = _session.get(url, headers=headers, timeout=25)
            if r.status_code == 200:
                _cache[url] = r.text
                return r.text
        except requests.RequestException:
            pass
        time.sleep(2 + attempt * 3)
    return ""


def parse_feed(data):
    """Το «¬/÷/~» format του Flashscore => λίστα από (tournament, event) dicts."""
    events = []
    tour = {}
    for chunk in data.split("~"):
        fields = {}
        for part in chunk.split("¬"):
            if "÷" in part:
                k, v = part.split("÷", 1)
                fields.setdefault(k, v)
        if "ZA" in fields:
            tour = fields
        elif "AA" in fields:
            events.append((tour, fields))
    return events


def _initial_feed(html, name):
    m = re.search(r'initialFeeds\["%s"\]\s*=\s*\{\s*data:\s*`(.*?)`' % re.escape(name), html, re.S)
    return m.group(1) if m else ""


def _event(tour, f):
    def num(k):
        v = f.get(k)
        return int(v) if v not in (None, "") and v.lstrip("-").isdigit() else None

    periods = []
    for hk, ak in (("BA", "BB"), ("BC", "BD"), ("BE", "BF"), ("BG", "BH"), ("BI", "BJ")):
        h, a = num(hk), num(ak)
        if h is not None and a is not None:
            periods.append((h, a))
    za = tour.get("ZA", "")
    return {
        "id": f["AA"],
        "start": int(f.get("AD", "0")),
        "status": f.get("AB", ""),  # 1 πρόγραμμα, 2 live, 3 τέλος
        "stage": f.get("AC", ""),
        "home": clean_team(f.get("AE", "")),
        "away": clean_team(f.get("AF", "")),
        "home_id": f.get("PX", ""),
        "away_id": f.get("PY", ""),
        "home_score": num("AG"),
        "away_score": num("AH"),
        "periods": periods,
        "round": f.get("ER", ""),
        "info": f.get("AM", "").replace("\n", " "),
        "comp_full": za,
        "comp": za.split(": ", 1)[-1],
        "tour_id": tour.get("ZEE", ""),
        "stage_id": tour.get("ZC", ""),
        "tour_path": tour.get("ZL", ""),
        "comp_logo": IMG + tour["OAJ"] if tour.get("OAJ") else "",
    }


def clean_team(name):
    """«Παναθηναϊκός Γ» => «Παναθηναϊκός» (το Γ = γυναικεία ομάδα στο Flashscore)."""
    return re.sub(r"\s+Γ$", "", name.strip())


def team_events(fs_path):
    """Όλοι οι αγώνες (πρόγραμμα + αποτελέσματα) στη σελίδα μιας ομάδας."""
    html = get(f"{BASE}/team/{fs_path}/")
    out = {}
    for name in ("summary-results", "summary-fixtures"):
        for tour, f in parse_feed(_initial_feed(html, name)):
            ev = _event(tour, f)
            out[ev["id"]] = ev
    return sorted(out.values(), key=lambda e: e["start"])


def match_page(event_id):
    """Το environment της σελίδας αγώνα: σήματα ομάδων, διοργάνωση με αγωνιστική."""
    html = get(f"{BASE}/match/{event_id}/")
    i = html.find("environment = {")
    if i < 0:
        return {}
    j = html.find("};", i)
    try:
        return json.loads(html[i + 14 : j + 1])
    except ValueError:
        return {}


def crests(event_id):
    env = match_page(event_id)
    pd = env.get("participantsData") or {}
    out = {}
    for side in ("home", "away"):
        p = (pd.get(side) or [{}])[0]
        out[side] = p.get("image_path") or ""
    return out


def tournament_title(event_id):
    env = match_page(event_id)
    return ((env.get("header") or {}).get("tournament") or {}).get("tournament", "")


def summary(event_id):
    """Γεγονότα αγώνα (γκολ κ.λπ.) και γήπεδο."""
    data = get(f"{BASE}/x/feed/df_sui_1_{event_id}", feed=True)
    goals = []
    venue = ""
    city = ""
    section = ""
    for chunk in data.split("~"):
        parts = [p.split("÷", 1) for p in chunk.split("¬") if "÷" in p]
        if not parts:
            continue
        keys = [k for k, _ in parts]
        if keys[0] == "AC":
            section = parts[0][1]
            continue
        if "MIT" in keys:
            for n, (k, v) in enumerate(parts):
                if k == "MIT" and n + 1 < len(parts):
                    if v == "VEN":
                        venue = parts[n + 1][1]
                    elif v == "TWN":
                        city = parts[n + 1][1]
            continue
        # Η διαδικασία των πέναλτι δεν μετράει στα γκολ.
        if keys[0] != "III" or "Πέναλτι" in section:
            continue
        f = {}
        for k, v in parts:
            f.setdefault(k, v)
        kind = f.get("IK", "")
        if f.get("IE") == "3" or "Αυτογκόλ" in kind:
            minute = f.get("IB", "")
            note = ""
            if "Αυτογκόλ" in kind:
                note = "αυτ."
            elif "Πέναλτι" in kind:
                note = "πέν."
            goals.append({"side": "home" if f.get("IA") == "1" else "away", "player": f.get("IF", ""), "minute": minute, "note": note})
    return {"goals": goals, "venue": venue, "city": city}


def standings(tour_id, stage_id):
    """Βαθμολογία (γραμμές) μιας φάσης διοργάνωσης."""
    data = get(f"{BASE}/x/feed/to_{tour_id}_{stage_id}_1", feed=True)
    if not data:
        return []
    logos = dict(re.findall(r"IPI÷([^¬]+)¬IPU÷([^¬]+)", data))
    rows = []
    for chunk in data.split("~"):
        if not chunk.startswith("TR÷"):
            continue
        f = {}
        for p in chunk.split("¬"):
            if "÷" in p:
                k, v = p.split("÷", 1)
                f.setdefault(k, v)
        gf, ga = (f.get("TG", "0:0").split(":") + ["0"])[:2]
        rows.append(
            {
                "rank": int(f.get("TR", 0) or 0),
                "name": clean_team(f.get("TN", "")),
                "id": f.get("TI", ""),
                "played": int(f.get("TM", 0) or 0),
                "w": int(f.get("TW", 0) or 0),
                "d": int(f.get("TDR", 0) or 0),
                "l": int(f.get("TL", 0) or 0),
                "gf": int(gf or 0),
                "ga": int(ga or 0),
                "pts": int(f.get("TP", 0) or 0),
                "logo": IMG + logos[f["TI"]] if f.get("TI") in logos else "",
            }
        )
    return rows


def round_finished(tour_path, round_label):
    """Έχουν τελειώσει όλοι οι αγώνες της αγωνιστικής; (σελίδα διοργάνωσης)"""
    if not tour_path or not round_label:
        return False
    html = get(f"{BASE}{tour_path}")
    data = _initial_feed(html, "summary-fixtures")
    if not data:
        return False
    for tour, f in parse_feed(data):
        if f.get("ER") == round_label and f.get("AB") in ("1", "2") and f.get("AC") not in OFF_STATES:
            return False
    return True
