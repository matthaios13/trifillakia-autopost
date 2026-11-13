"""Βαθμολογίες για τη σελίδα «Βαθμολογίες» του trifillakia.gr.

Γράφει docs/standings.json (GitHub Pages) με τέσσερις πίνακες:
- superleague : Stoiximan Super League (ESPN)
- cup         : Superbet Κύπελλο Ελλάδας — league phase (Wikipedia)
- gbl         : Stoiximan GBL (ΕΣΑΚΕ)
- euroleague  : EuroLeague (επίσημο API)

Το site (block 41, standings.js) διαβάζει το JSON και φτιάχνει τους πίνακες.
Ανανεώνεται το πολύ κάθε 30′ (το bot τρέχει κάθε 5′).
"""
import html
import json
import os
import re
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "standings.json")
UA = {"User-Agent": "Mozilla/5.0 (trifillakia standings)"}
EVERY = 30 * 60

GR = {
    "Panathinaikos": "Παναθηναϊκός", "Olympiacos": "Ολυμπιακός", "AEK Athens": "ΑΕΚ", "PAOK": "ΠΑΟΚ",
    "PAOK Salonika": "ΠΑΟΚ", "Aris": "Άρης", "Aris Thessaloniki": "Άρης", "OFI Crete": "ΟΦΗ", "OFI": "ΟΦΗ",
    "Asteras Tripolis": "Αστέρας Τρίπολης", "Asteras Tripoli": "Αστέρας Τρίπολης", "A.E. Kifisia": "Κηφισιά",
    "Niki Volos": "Νίκη Βόλου", "Nestos Chrysoupoli": "Νέστος Χρυσούπολης", "Nestos": "Νέστος Χρυσούπολης", "Marko": "Μαρκό", "Asteras Aktor": "Αστέρας Τρίπολης", "Volos": "Βόλος",
    "Volos NFC": "Βόλος", "Levadiakos": "Λεβαδειακός", "Panserraikos": "Πανσερραϊκός", "Atromitos": "Ατρόμητος",
    "Kifisia": "Κηφισιά", "AE Kifisia": "Κηφισιά", "Panetolikos": "Παναιτωλικός", "AEL": "ΑΕΛ",
    "AEL Larissa": "ΑΕΛ", "Larissa": "ΑΕΛ", "Lamia": "Λαμία", "Athens Kallithea": "Καλλιθέα",
    "Kallithea": "Καλλιθέα", "Panionios": "Πανιώνιος", "Iraklis": "Ηρακλής", "Heraklis": "Ηρακλής",
    "Marko": "Μαρκό", "Chania": "Χανιά", "Ilioupoli": "Ηλιούπολη", "Kalamata": "Καλαμάτα",
}


def _get(url, as_json=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        data = r.read().decode("utf-8", "ignore")
    return json.loads(data) if as_json else data


GBL = {
    "ΠΑΝΑΘΗΝΑΙΚΟΣ": "Παναθηναϊκός", "ΟΛΥΜΠΙΑΚΟΣ": "Ολυμπιακός", "ΑΕΚ": "ΑΕΚ", "ΠΑΟΚ": "ΠΑΟΚ", "ΑΡΗΣ": "Άρης",
    "ΠΡΟΜΗΘΕΑΣ": "Προμηθέας", "ΠΕΡΙΣΤΕΡΙ": "Περιστέρι", "ΚΟΛΟΣΣΟΣ": "Κολοσσός", "ΜΑΡΟΥΣΙ": "Μαρούσι",
    "ΛΑΥΡΙΟ": "Λαύριο", "ΜΥΚΟΝΟΣ": "Μύκονος", "ΗΡΑΚΛΗΣ": "Ηρακλής", "ΚΑΡΔΙΤΣΑ": "Καρδίτσα",
    "ΑΠΟΛΛΩΝ": "Απόλλων", "ΔΟΞΑ": "Δόξα Λευκάδας", "VIKOS": "Vikos Falcons", "ΜΑΚΕΔΟΝΙΚΟΣ": "Μακεδονικός", "ΠΑΝΙΩΝΙΟΣ": "Πανιώνιος", "ΑΜΑΡΟΥΣΙΟΣ": "Αμαρούσιος",
}
CUPLOGO = {
}
ELGR = {"Panathinaikos": "Παναθηναϊκός", "Olympiacos": "Ολυμπιακός"}


def gr(name):
    return GR.get(name, name)


def gbl_name(raw):
    import unicodedata
    key = "".join(ch for ch in unicodedata.normalize("NFD", raw.upper()) if unicodedata.category(ch) != "Mn")
    for k, v in GBL.items():
        if key.startswith(k):
            return v
    w = raw.strip().split()
    return " ".join(x[:1] + x[1:].lower() for x in w)


def superleague():
    d = _get("https://site.api.espn.com/apis/v2/sports/soccer/gre.1/standings", True)
    ent = d["children"][0]["standings"]["entries"]
    rows, logos = [], {}
    for e in ent:
        s = {x["name"]: x.get("value") for x in e["stats"]}
        t = e["team"]
        logo = (t.get("logos") or [{}])[0].get("href", "")
        logos[t["displayName"]] = logo
        rows.append({
            "pos": int(s.get("rank") or 0), "team": gr(t["displayName"]), "logo": logo,
            "pld": int(s.get("gamesPlayed") or 0), "w": int(s.get("wins") or 0), "d": int(s.get("ties") or 0),
            "l": int(s.get("losses") or 0), "gf": int(s.get("pointsFor") or 0), "ga": int(s.get("pointsAgainst") or 0),
            "pts": int(s.get("points") or 0),
        })
    rows.sort(key=lambda r: r["pos"])
    return {"title": "Stoiximan Super League", "kind": "football", "rows": rows}, logos


def cup(espn_logos):
    api = "https://en.wikipedia.org/w/api.php?action=parse&format=json&prop=sections&page="
    page = "2026%E2%80%9327_Greek_Football_Cup"
    secs = _get(api + page, True)["parse"]["sections"]
    idx = next(s["index"] for s in secs if s["line"].strip().lower() == "league phase table")
    t = _get(f"https://en.wikipedia.org/w/api.php?action=parse&format=json&prop=text&section={idx}&page={page}", True)
    h = t["parse"]["text"]["*"]
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S):
        c = [html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        if len(c) < 10 or not c[0].isdigit():
            continue
        name = re.sub(r"\s*\(.*?\)", "", c[1]).strip()
        bygr = {gr(k): v for k, v in espn_logos.items()}
        logo = espn_logos.get(name) or bygr.get(gr(name)) or next((v for k, v in espn_logos.items() if k.startswith(name) or name.startswith(k)), "") or CUPLOGO.get(gr(name), "")
        rows.append({"pos": int(c[0]), "team": gr(name), "logo": logo, "pld": int(c[2]), "w": int(c[3]),
                     "d": int(c[4]), "l": int(c[5]), "gf": int(c[6]), "ga": int(c[7]),
                     "pts": int(re.sub(r"\D", "", c[9]) or 0), "note": c[10] if len(c) > 10 else ""})
    return {"title": "Superbet Κύπελλο Ελλάδας — League phase", "kind": "football", "rows": rows}


def gbl():
    h = _get("https://www.esake.gr/el/action/EsakeRanking")
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S):
        c = [html.unescape(re.sub(r"<[^>]+>", " ", x)).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        c = [re.sub(r"\s+", " ", x) for x in c if x.strip()]
        if len(c) < 7:
            continue
        m = re.match(r"(\d+)\s*(.+)", c[0])
        if not m:
            continue
        img = re.findall(r'<img[^>]+src="([^"]+)"', tr)
        wl = re.findall(r"\d+", c[3])
        pf = re.findall(r"\d+", c[6])
        rows.append({"pos": int(m.group(1)), "team": gbl_name(m.group(2)), "logo": ("https://www.esake.gr" + img[0]) if img else "",
                     "pld": int(c[2]), "w": int(wl[0]) if wl else 0, "l": int(wl[1]) if len(wl) > 1 else 0,
                     "pf": int(pf[0]) if pf else 0, "pa": int(pf[1]) if len(pf) > 1 else 0, "pts": int(c[1])})
    rows.sort(key=lambda r: r["pos"])
    return {"title": "Stoiximan GBL", "kind": "basket", "rows": rows}


def euroleague():
    x = _get("https://api-live.euroleague.net/v1/standings?seasonCode=E2026")
    rnd = max(int(n) for n in re.findall(r'gamenumber="(\d+)"', x) or ["1"])
    d = None
    for r in range(rnd, max(rnd - 3, 0), -1):
        try:
            d = _get(f"https://feeds.incrowdsports.com/provider/euroleague-feeds/v3/competitions/E/seasons/E2026/rounds/{r}/basicstandings", True)
            if d.get("teams"):
                break
        except Exception:  # noqa: BLE001
            d = None
    rows = []
    for t in (d or {}).get("teams", []):
        cl = t.get("club", {})
        imgs = cl.get("images") or {}
        rows.append({"pos": t.get("position"), "team": ELGR.get(cl.get("abbreviatedName") or "", cl.get("abbreviatedName") or cl.get("name")),
                     "logo": imgs.get("crest", ""), "pld": t.get("gamesPlayed"), "w": t.get("gamesWon"),
                     "l": t.get("gamesLost"), "pf": t.get("pointsFor"), "pa": t.get("pointsAgainst"),
                     "pct": t.get("winPercentage"), "pts": t.get("gamesWon")})
    return {"title": "EuroLeague", "kind": "basket", "round": rnd, "rows": rows}


def update(log=print, force=False):
    if not force and os.path.exists(OUT) and time.time() - os.path.getmtime(OUT) < EVERY:
        return
    old = {}
    if os.path.exists(OUT):
        try:
            with open(OUT, encoding="utf-8") as fh:
                old = json.load(fh).get("comps", {})
        except Exception:  # noqa: BLE001
            old = {}
    comps, logos = dict(old), {}
    for key, fn in (("superleague", superleague), ("cup", None), ("gbl", gbl), ("euroleague", euroleague)):
        try:
            if key == "superleague":
                comps[key], logos = fn()
            elif key == "cup":
                comps[key] = cup(logos)
            else:
                comps[key] = fn()
            if not comps[key].get("rows"):
                raise ValueError("κενός πίνακας")
        except Exception as e:  # noqa: BLE001
            log("Βαθμολογία", key, "σφάλμα:", e)
            if key in old:
                comps[key] = old[key]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"updated": int(time.time()), "comps": comps}, fh, ensure_ascii=False)
    log("Βαθμολογίες:", {k: len(v.get("rows", [])) for k, v in comps.items()})


if __name__ == "__main__":
    update(force=True)
