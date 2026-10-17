"""Λεζάντες (ύφος @trifillakiagr)."""
from datetime import datetime

from .config import TZ

DAYS = ["Δευτέρα", "Τρίτη", "Τετάρτη", "Πέμπτη", "Παρασκευή", "Σάββατο", "Κυριακή"]
MONTHS = ["Ιανουαρίου", "Φεβρουαρίου", "Μαρτίου", "Απριλίου", "Μαΐου", "Ιουνίου", "Ιουλίου", "Αυγούστου", "Σεπτεμβρίου", "Οκτωβρίου", "Νοεμβρίου", "Δεκεμβρίου"]


def date_line(ts):
    dt = datetime.fromtimestamp(ts, TZ)
    return f"{DAYS[dt.weekday()]} {dt.day} {MONTHS[dt.month - 1]}", dt.strftime("%H:%M")


def _pao_home(m):
    return "Παναθηναϊκός" in m["home"]


def _foot(team):
    return f"\n\n{team['tags']}\n\n{team['mentions']}"


def gameday(m, team):
    day, hour = date_line(m["start"])
    lines = [
        f"🟢 GAME DAY | {team['name']} ☘️",
        "",
        f"{team['emoji']} {m['home']} – {m['away']}",
        f"🏆 {m['comp']}" + (f" | {m['round']}" if m.get("round") else ""),
        f"🗓️ {day} | ⏰ {hour}",
    ]
    if m.get("venue"):
        lines.append(f"📍 {m['venue']}")
    lines += ["", "Όλοι μαζί, πάμε Παναθηναϊκέ! 💚"]
    return "\n".join(lines) + _foot(team)


def fulltime(m, team):
    ours, theirs = (m["home_score"], m["away_score"]) if _pao_home(m) else (m["away_score"], m["home_score"])
    if ours > theirs:
        line = "Το «Τριφύλλι» πήρε τη νίκη! 💚"
    elif ours == theirs:
        line = "Μοιρασιά βαθμών για το «Τριφύλλι»."
    else:
        line = "Ήττα για το «Τριφύλλι». Πάμε για το επόμενο! 💚"
    lines = [
        f"🟢 FINAL SCORE | {team['name']}",
        "",
        f"{team['emoji']} {m['home']} {m['home_score']}-{m['away_score']} {m['away']} ☘️",
        f"🏆 {m['comp']}" + (f" | {m['round']}" if m.get("round") else ""),
    ]
    if m.get("goals"):
        for side in ("home", "away"):
            gl = [f"{g['player']} {g['minute']}" + (f" ({g['note']})" if g["note"] else "") for g in m["goals"] if g["side"] == side]
            if gl:
                lines.append(f"⚽ {m[side]}: " + ", ".join(gl))
    if m.get("periods") and m["sport"] != "football":
        lines.append("📊 " + " | ".join(f"{h}-{a}" for h, a in m["periods"]))
    if m.get("info"):
        lines.append(f"ℹ️ {m['info']}")
    lines += ["", line]
    return "\n".join(lines) + _foot(team)


def standings(m, team):
    pos = next((r for r in m["rows"] if r["id"] == m["pao_id"]), None)
    lines = [f"📊 Η βαθμολογία | {m['comp']}" + (f" | {m['round']}" if m.get("round") else "") + " ☘️", ""]
    if pos:
        rec = f"{pos['w']}-{pos['d']}-{pos['l']}" if m["sport"] in ("football", "water-polo") else f"{pos['w']}-{pos['l']}"
        lines.append(f"Ο Παναθηναϊκός στην {pos['rank']}η θέση με {pos['pts']} βαθμούς ({rec}).")
    return "\n".join(lines) + _foot(team)


def mvp(m, team):
    names = {"ΠΟΝΤΟΙ": "πόντοι", "ΡΙΜΠΑΟΥΝΤ": "ριμπάουντ", "ΑΣΙΣΤ": "ασίστ", "ΚΛΕΨΙΜΑΤΑ": "κλεψίματα"}
    stats = " | ".join(f"{int(round(float(v or 0)))} {names.get(l, l)}" for v, l in m["stats"])
    return (
        f"🏆 MVP | {m['first']} {m['last']} ☘️\n\n"
        f"🏀 {m['home']} {m['score']} {m['away']} ({m['comp']})\n"
        f"📊 {stats}" + _foot(team)
    )


NEWS_TAGS = {
    "podosfairo": "#Panathinaikos #PAO #Παναθηναϊκός #Τριφύλλι #trifillakiagr",
    "mpasket": "#Panathinaikos #PAOBC #Παναθηναϊκός #Τριφύλλι #trifillakiagr",
    "mpasket-gynaikon": "#Panathinaikos #WomensBasketball #Παναθηναϊκός #trifillakiagr",
    "erasitehnis": "#Panathinaikos #ΠαναθηναϊκόςΑΟ #Παναθηναϊκός #trifillakiagr",
}


def _short(text, n):
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n].rsplit(" ", 1)[0].rstrip(".,;:") + "…"


def news_ig(a):
    tags = NEWS_TAGS.get(a["section"], "#Panathinaikos #Παναθηναϊκός #Τριφύλλι #trifillakiagr")
    lines = [f"📰 {a['title']} ☘️", ""]
    if a.get("description"):
        lines += [_short(a["description"], 400), ""]
    lines += ["🔗 Ολόκληρο το άρθρο στο link του bio", "", tags]
    return "\n".join(lines)


def news_fb(a):
    text = f"☘️ {a['title']}"
    if a.get("description"):
        text += "\n\n" + _short(a["description"], 220)
    return text
