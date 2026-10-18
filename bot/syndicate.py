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


# Λέξεις που υπάρχουν σχεδόν σε κάθε άρθρο και δεν ξεχωρίζουν μια είδηση.
STOP = {
    "παναθηναικος", "παναθηναικου", "παναθηναικο", "πρασινοι", "πρασινων", "τριφυλλι", "aktor",
    "για", "στην", "στον", "στο", "στη", "των", "του", "της", "τον", "την", "και", "που", "από", "απο",
    "με", "σε", "να", "θα", "ειναι", "μετα", "πριν", "οι", "τα", "το", "η", "ο", "ενα", "μια", "δεν",
}


def _norm_words(text):
    """Οι «σημαντικές» λέξεις ενός κειμένου, χωρίς τόνους, κομμένες στα 5 γράμματα (για καταλήξεις)."""
    t = unicodedata.normalize("NFD", html.unescape(re.sub(r"<[^>]+>", " ", text)).lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return {w[:5] for w in re.findall(r"[a-zα-ω0-9]+", t) if len(w) >= 3 and w not in STOP}


def similar(a, b):
    """Ίδια είδηση; (κοινές λέξεις τίτλου)"""
    wa, wb = _norm_words(a), _norm_words(b)
    if not wa or not wb:
        return False
    common = len(wa & wb)
    return (common >= 4 and common / min(len(wa), len(wb)) >= 0.75) or common / len(wa | wb) >= 0.5


def same_story(title, doc):
    """doc = (τίτλος, κείμενο) άρθρου του trifillakia. Ίδια είδηση μόνο αν μοιάζουν πολύ οι τίτλοι
    (η σύγκριση με το κείμενο έβγαζε λάθος ταυτίσεις, π.χ. συνέχειες της ίδιας ιστορίας)."""
    return similar(title, doc[0])


def trifillakia_docs(extra=()):
    """(τίτλος, κείμενο) των πρόσφατων άρθρων του trifillakia.gr (ροές κατηγοριών)."""
    docs = [(t, "") for t in extra]
    for url in TRIFILLAKIA_FEEDS:
        try:
            r = _s.get(url, timeout=30)
        except requests.RequestException:
            continue
        for item in re.findall(r"<item>(.*?)</item>", r.text, re.S):
            t = re.search(r"<title>(.*?)</title>", item, re.S)
            d = re.search(r"<description>(.*?)</description>", item, re.S)
            docs.append((html.unescape(t.group(1)) if t else "", html.unescape(d.group(1)) if d else ""))
    return docs


def _media_url(posts_base, media_id):
    if not media_id:
        return ""
    try:
        r = _s.get(posts_base.replace("/posts", f"/media/{media_id}") + "?_fields=source_url", timeout=30)
        return (r.json() or {}).get("source_url", "") if r.status_code == 200 else ""
    except (requests.RequestException, ValueError):
        return ""


PAO = "Παναθηναϊκ"


def _plain(text):
    t = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def pao_tag_ids(posts_base):
    """Όλα τα tags με «Παναθηναϊκ» στο όνομα (Κ19, Κ17, Ακαδημίες, AKTOR...)."""
    try:
        r = _s.get(posts_base.replace("/posts", "/tags") + "?search=" + PAO + "&per_page=100&_fields=id,name", timeout=30)
        tags = r.json() if r.status_code == 200 else []
    except (requests.RequestException, ValueError):
        tags = []
    return [str(t["id"]) for t in tags if isinstance(t, dict) and _plain(PAO) in _plain(t.get("name", ""))]


PAO_WORDS = ("παναθηναικ", "πρασιν", "τριφυλλ")


def about_pao(title, body, title_only=False):
    """Είδηση του Παναθηναϊκού; Ο τίτλος ή η αρχή του κειμένου (lead) πρέπει να τον αναφέρει.
    Το tag μόνο του δεν αρκεί (π.χ. «Πουλακίδας» με λάθος tag Παναθηναϊκός)."""
    if any(w in _plain(title) for w in PAO_WORDS):
        return True
    if title_only:
        return False
    lead = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body))).strip()[:400]
    return any(w in _plain(lead) for w in PAO_WORDS)


def fetch(source, since_ts):
    name, base, filters, category = source
    seen = {}
    filters = list(filters)
    ids = pao_tag_ids(base)
    if ids:
        filters.append("tags=" + ",".join(ids))
    # Δίχτυ ασφαλείας: «Παναθηναϊκ» στον τίτλο, ακόμα κι αν δεν έχει σωστό tag.
    filters.append("search=" + PAO)
    for f in filters:
        title_only = f.startswith("search=")
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
            if not about_pao(title, p["content"]["rendered"], title_only):
                continue
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
    state.setdefault("blocked", [])
    state["items"] = [i for i in state["items"] if i["guid"] not in state["blocked"]]
    have = {i["guid"] for i in state["items"]} | set(state["blocked"])
    candidates = []
    for src in SOURCES:
        candidates += [p for p in fetch(src, state["since"]) if p["guid"] not in have]
    if candidates:
        existing = trifillakia_docs(extra=[i["title"] for i in state["items"]])
        for p in sorted(candidates, key=lambda p: p["ts"]):
            if any(same_story(p["title"], d) for d in existing):
                log("Ροή trifillakia: υπάρχει ήδη →", p["title"])
                continue
            state["items"].append(p)
            existing.append((p["title"], ""))
            log("Ροή trifillakia: νέο άρθρο ←", p["source"], p["title"])
    state["items"] = sorted(state["items"], key=lambda i: -i["ts"])[:30]
    write_feed(state["items"])
    return state
