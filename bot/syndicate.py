"""Άρθρα για τον Παναθηναϊκό από bala24.gr (ποδόσφαιρο) και totalbasket.gr (μπάσκετ) → trifillakia.gr.

Το trifillakia.gr (Drupal 7) έχει CAPTCHA στο login, οπότε δεν γράφουμε απευθείας: φτιάχνουμε ένα RSS
(docs/pao-feed.xml στο GitHub Pages) και το module Feeds του Drupal το τραβάει και δημιουργεί τα άρθρα
(importer «pao_news», ίδια λογική με τον «ELABET άρθρα»).

Ένα άρθρο μπαίνει μόνο αν δεν υπάρχει ήδη στο trifillakia.gr με παρόμοιο τίτλο.
"""
import html
import os
import re
import unicodedata
from datetime import datetime, timezone
from email.utils import format_datetime

import requests

from .cards import ROOT
from .flashscore import UA

FEED = os.path.join(ROOT, "docs", "pao-feed.xml")

SOURCES = [
    # (όνομα, βάση REST, φίλτρα, κατηγορία στο trifillakia, συντάκτης)
    ("bala24.gr", "https://bala24.gr/wp-json/wp/v2/posts", ["categories=55", "tags=47"], "Ποδοσφαιρο"),
    ("totalbasket.gr", "https://totalbasket.gr/wp-json/wp/v2/posts", ["tags=137"], "Μπασκετ"),
]
TRIFILLAKIA_FEEDS = [f"https://www.trifillakia.gr/taxonomy/term/{t}/feed" for t in (1, 2, 4, 5)]

_s = requests.Session()
_s.headers.update({"User-Agent": UA})


def _norm_words(title):
    t = unicodedata.normalize("NFD", html.unescape(title).lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return {w for w in re.findall(r"[a-zα-ω0-9]+", t) if len(w) >= 4}


def similar(a, b):
    """Ίδια είδηση; (κοινές λέξεις τίτλου)"""
    wa, wb = _norm_words(a), _norm_words(b)
    if not wa or not wb:
        return False
    common = len(wa & wb)
    return common / min(len(wa), len(wb)) >= 0.6 or common / len(wa | wb) >= 0.45


def trifillakia_titles(extra=()):
    titles = list(extra)
    for url in TRIFILLAKIA_FEEDS:
        try:
            r = _s.get(url, timeout=30)
            titles += [html.unescape(t) for t in re.findall(r"<title>(.*?)</title>", r.text)[1:]]
        except requests.RequestException:
            pass
    return titles


def _media_url(posts_base, media_id):
    if not media_id:
        return ""
    try:
        r = _s.get(posts_base.replace("/posts", f"/media/{media_id}") + "?_fields=source_url", timeout=30)
        return (r.json() or {}).get("source_url", "") if r.status_code == 200 else ""
    except (requests.RequestException, ValueError):
        return ""


def fetch(source, since_ts):
    name, base, filters, category = source
    seen = {}
    for f in filters:
        try:
            r = _s.get(f"{base}?{f}&per_page=20&_fields=id,date_gmt,title,link,content,featured_media", timeout=40)
            posts = r.json() if r.status_code == 200 else []
        except (requests.RequestException, ValueError):
            posts = []
        for p in posts if isinstance(posts, list) else []:
            ts = datetime.fromisoformat(p["date_gmt"]).replace(tzinfo=timezone.utc).timestamp()
            if ts < since_ts:
                continue
            title = html.unescape(re.sub(r"<[^>]+>", "", p["title"]["rendered"])).strip()
            if title.upper().startswith("ELABET"):
                continue  # τα προγνωστικά έχουν δικό τους importer
            image = _media_url(base, p.get("featured_media"))
            seen[f"{name}:{p['id']}"] = {
                "guid": f"{name}:{p['id']}",
                "source": name,
                "category": category,
                "title": title,
                "link": p["link"],
                "body": p["content"]["rendered"],
                "image": image,
                "ts": ts,
            }
    return list(seen.values())


def _item(it):
    pub = format_datetime(datetime.fromtimestamp(it["ts"], timezone.utc))
    img = f'<source url="{html.escape(it["image"])}">fa-file-text</source>' if it["image"] else "<source>fa-file-text</source>"
    return (
        "<item>"
        f"<title>{html.escape(it['title'])}</title>"
        f"<link>{html.escape(it['link'])}</link>"
        f"<description>{html.escape(it['body'])}</description>"
        f"<category>{html.escape(it['category'])}</category>"
        f'<guid isPermaLink="false">{html.escape(it["guid"])}</guid>'
        f"<author>{html.escape(it['source'])}</author>"
        f"<pubDate>{pub}</pubDate>"
        f"{img}"
        "</item>"
    )


def write_feed(items):
    os.makedirs(os.path.dirname(FEED), exist_ok=True)
    xml = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<rss version="2.0"><channel>'
        "<title>Trifillakia – Παναθηναϊκός από bala24 / totalbasket</title>"
        "<link>https://www.trifillakia.gr</link>"
        "<description>Αυτόματη ροή για το Feeds του trifillakia.gr</description>"
        + "".join(_item(i) for i in sorted(items, key=lambda i: -i["ts"]))
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


def update(state, now, log=print):
    """Νέα άρθρα στη ροή. state: {"since": ts, "items": [...]} (κρατά τα 30 τελευταία)."""
    if not state.get("since"):
        state["since"] = now  # ξεκινάμε από τώρα, χωρίς παλιά άρθρα
        state["items"] = []
        write_feed([])
        return state
    have = {i["guid"] for i in state["items"]}
    candidates = []
    for src in SOURCES:
        candidates += [p for p in fetch(src, state["since"]) if p["guid"] not in have]
    if candidates:
        existing = trifillakia_titles(extra=[i["title"] for i in state["items"]])
        for p in sorted(candidates, key=lambda p: p["ts"]):
            if any(similar(p["title"], t) for t in existing):
                log("Ροή trifillakia: υπάρχει ήδη →", p["title"])
                continue
            state["items"].append(p)
            existing.append(p["title"])
            log("Ροή trifillakia: νέο άρθρο ←", p["source"], p["title"])
    state["items"] = sorted(state["items"], key=lambda i: -i["ts"])[:30]
    write_feed(state["items"])
    return state
