"""Εκπομπές του καναλιού @trifillakia_gr → άρθρα «Video» στο trifillakia.gr (κουτί «Τελευταίο Βίντεο»).

Το κουτί «Τελευταίο Βίντεο» δείχνει το πιο πρόσφατο άρθρο με post format «Video» (fa-play-circle-o).
Κάθε live του καναλιού (λίστα UULV), μόλις ξεκινήσει ή τελειώσει, μπαίνει στο docs/shows-feed.xml και ο
importer «Εκπομπές YouTube» (trifillakia_shows) του Drupal Feeds φτιάχνει άρθρο στην κατηγορία PODCAST με
το βίντεο ενσωματωμένο. Οι προγραμματισμένες εκπομπές (δεν έχουν ξεκινήσει) δεν μπαίνουν.
Αν υπάρχει ήδη άρθρο με ίδιο τίτλο (π.χ. το ανέβασε συντάκτης), δεν ξαναμπαίνει.
"""
import html
import os
import re
import time
from datetime import datetime, timezone

from . import youtube
from .cards import ROOT
from .syndicate import _item, _plain, _s

FEED = os.path.join(ROOT, "docs", "shows-feed.xml")
# Από τη μέρα μετά το τελευταίο GREEN VOICE (26/10) που υπήρχε ήδη στο PODCAST: ό,τι παλιότερο δεν μπαίνει.
SINCE = datetime(2026, 10, 27, tzinfo=timezone.utc).timestamp()
CATEGORY = "PODCAST"
FORMAT = "fa-play-circle-o"
PODCAST_FEED = "https://www.trifillakia.gr/taxonomy/term/3766/feed"


def _clean_title(title):
    t = "".join(c for c in title if ord(c) <= 0xFFFF and c not in "️🟢")
    t = re.sub(r"^\W*LIVE\b\s*", "", t.strip(), flags=re.I)
    t = re.sub(r"\s*\|\s*", " | ", t)
    return " ".join(t.split()).strip(" |-–")


def _existing_titles():
    try:
        r = _s.get(PODCAST_FEED, params={"nc": int(time.time())}, timeout=30)
        return {_plain(html.unescape(t)) for t in re.findall(r"<title>(.*?)</title>", r.text)[1:]}
    except Exception:  # noqa: BLE001
        return set()


def _body(v):
    vid = v["id"]
    return (
        f'<p><iframe width="100%" height="400" src="https://www.youtube.com/embed/{vid}" '
        'title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; '
        'encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe></p>'
        f"<p>{html.escape(v['topic'] or v['title'])}</p>"
        f'<p>Δείτε ολόκληρη την εκπομπή στο κανάλι μας στο YouTube: '
        f'<a href="{v["url"]}" target="_blank">{youtube.CHANNEL_URL}</a></p>'
    )


def update(state, log=print):
    """state: {"items": [...]} — κρατά τις 15 πιο πρόσφατες εκπομπές που έχουν ήδη ξεκινήσει."""
    r = _s.get(youtube.FEED, params={"nc": int(time.time())}, timeout=30)
    if r.status_code != 200:
        log(f"Εκπομπές: το YouTube απάντησε {r.status_code}")
        return False
    have = {i["guid"] for i in state.setdefault("items", [])}
    existing = None
    for e in re.findall(r"<entry>(.*?)</entry>", r.text, re.S)[:10]:
        vid = re.search(r"<yt:videoId>(.*?)</yt:videoId>", e)
        pub = re.search(r"<published>(.*?)</published>", e)
        if not vid or not pub:
            continue
        guid = f"yt-show:{vid.group(1)}"
        if guid in have:
            continue
        pts = datetime.fromisoformat(pub.group(1).replace("Z", "+00:00")).timestamp()
        if pts < SINCE:
            continue
        v = youtube.video(vid.group(1))
        if not v:
            continue
        # Από τους servers του GitHub η σελίδα του YouTube έρχεται συχνά χωρίς στοιχεία (consent/bot check):
        # τότε ο τίτλος παίρνεται από το RSS και «δεν έχει ξεκινήσει» = 0 προβολές.
        if not v["title"]:
            ft = re.search(r"<title>(.*?)</title>", e, re.S)
            views = re.search(r'<media:statistics views="(\d+)"', e)
            v["title"] = html.unescape(ft.group(1)).strip() if ft else ""
            v["topic"] = youtube._split_title(v["title"])[1]
            v["upcoming"] = not views or views.group(1) == "0"
        if v["upcoming"]:
            continue  # δεν έχει ξεκινήσει ακόμα
        title = _clean_title(v["title"])
        if not title:
            continue  # το YouTube δεν έδωσε τίτλο: ξανά στον επόμενο κύκλο, όχι άρθρο χωρίς τίτλο
        if existing is None:
            existing = _existing_titles()
        if _plain(title) in existing:
            log("Εκπομπές: υπάρχει ήδη στο trifillakia →", title)
            state["items"].append({"guid": guid, "skip": True, "ts": pts})
            continue
        state["items"].append({
            "guid": guid,
            "source": "YouTube",
            "category": CATEGORY,
            "title": title,
            "link": v["url"],
            "body": _body(v),
            "image": v["image"],
            "ts": v["start"] or pts,
            "format": FORMAT,
        })
        log("Εκπομπές: νέο άρθρο βίντεο ←", title)
    state["items"] = sorted(state["items"], key=lambda i: -i["ts"])[:15]
    items = [i for i in state["items"] if not i.get("skip")]
    xml = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<rss version="2.0"><channel>'
        "<title>Trifillakia – Εκπομπές YouTube</title>"
        "<link>https://www.trifillakia.gr</link>"
        "<description>Αυτόματη ροή εκπομπών για το Feeds του trifillakia.gr</description>"
        + "".join(_item(i).replace(">fa-file-text</source>", f">{i['format']}</source>") for i in items)
        + "</channel></rss>\n"
    )
    try:
        with open(FEED, encoding="utf-8") as fh:
            if fh.read() == xml:
                return False
    except OSError:
        pass
    with open(FEED, "w", encoding="utf-8") as fh:
        fh.write(xml)
    return True
