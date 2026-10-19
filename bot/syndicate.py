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
from email.utils import format_datetime, parsedate_to_datetime

import io

import requests
from PIL import Image

from .cards import ROOT
from .flashscore import UA

FEED = os.path.join(ROOT, "docs", "pao-feed.xml")
IMG_DIR = os.path.join(ROOT, "docs", "img")
PAGES = "https://matthaios13.github.io/trifillakia-autopost/"
# Το Drupal 7 του trifillakia δέχεται μόνο αυτές τις μορφές στο πεδίο εικόνας.
DRUPAL_IMG = (".jpg", ".jpeg", ".png", ".gif")

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


# Ομάδες: δεν μετράνε ως «πρόσωπο» της είδησης (ο ίδιος αντίπαλος εμφανίζεται σε πολλές διαφορετικές ειδήσεις).
TEAMS = (
    "ολυμπ", "αεκ", "παοκ", "αρη", "αρης", "αστερ", "οφη", "λεβαδ", "βολο", "βολος", "ατρομ", "πανσε", "κηφισ",
    "παναι", "αελ", "περισ", "προμη", "κολοσ", "μαρου", "λαυρι", "καρδι", "μυκον", "χαποε", "μακαμ", "ρεαλ",
    "μπαρτ", "φενερ", "εφες", "αναντ", "μονακ", "βιλερ", "παρτι", "ερυθρ", "ζαλγκ", "μπαγε", "βιρτο",
    "ολιμπ", "αρμαν", "μπασκ", "βαλεν", "παρι", "ντουμ", "καιρα", "τελ", "αβιβ", "οακα", "aktor", "super",
    "league", "euroleague", "stoiximan", "gbl", "εθνικ", "ελλαδ",
)
SCORE = re.compile(r"(?<![\d.])(\d{1,3})\s*[-–]\s*(\d{1,3})(?![\d.])")
WINDOW = 18 * 3600  # ίδια είδηση = μέσα σε 18 ώρες


def _names(title):
    """Ονόματα (λέξεις με κεφαλαίο στη μέση της φράσης) του τίτλου, χωρίς ομάδες, π.χ. {"ουναι"}."""
    out = set()
    for part in re.split(r"[:–—«»\"“”()|!?]|\s-\s", html.unescape(title)):
        words = re.findall(r"[^\W\d_][^\W_]*", part)
        for w in words[1:]:
            if w[0].isupper() and len(w) >= 3:
                full = _plain(w)
                k = full[:5]
                if full not in STOP and not k.startswith(TEAMS) and not any(x in full for x in PAO_WORDS):
                    out.add(k)
    return out


_LAT = str.maketrans("αβγδεζηθικλμνξοπρσςτυφχψω", "avgdeziuiklmnxoprsstyfxpo")


def _lat(text):
    """Ελληνικά → λατινικά (χοντρικά), για τίτλους γραμμένους μισά-μισά, π.χ. «Αsteras»."""
    return _plain(text).translate(_LAT)


def _score(text):
    m = SCORE.search(text)
    return f"{m.group(1)}-{m.group(2)}" if m else ""


def _opponent(title):
    """Ο αντίπαλος σε τίτλο αγώνα «Παναθηναϊκός – Αστέρας AKTOR (5-1): …» → "αστερ"."""
    head = re.split(r"[:(]", html.unescape(title))[0]
    for w in re.findall(r"[^\W\d_]+", head):
        full = _plain(w)
        if len(full) >= 3 and full not in STOP and not any(x in full for x in PAO_WORDS):
            return full[:5]
    return ""


def same_story(title, doc):
    """doc = {"title", "body", "ts"}: άρθρο του trifillakia ή άρθρο που μπήκε ήδη στη ροή. Ίδια είδηση αν:
    1. μοιάζουν πολύ οι τίτλοι, ή
    2. ο τίτλος έχει σκορ (τελικό αποτέλεσμα) και το άλλο άρθρο γράφει το ίδιο σκορ με τον ίδιο αντίπαλο
       (π.χ. ο συντάκτης του trifillakia έγραψε ήδη το ματς με δικό του τίτλο), ή
    3. μιλάνε για το ίδιο πρόσωπο και έχουν κι άλλη κοινή λέξη (π.χ. τρία άρθρα για τον τραυματισμό του Ουναΐ),
       αλλά όχι οι δηλώσεις ενός προσώπου σκέτες (Ομπράντοβιτς για Ναν ≠ «Επιστρέφει ο Ναν»)."""
    if similar(title, doc["title"]):
        return True
    # Ο κανόνας του σκορ μόνο για τίτλους ρεπορτάζ (σκορ πριν από την «:»), όχι για άρθρα που απλώς
    # αναφέρουν το αποτέλεσμα (π.χ. «Παναθηναϊκός: 26 τελικές και 5,72 xGoals στο 5-1» = στατιστικά).
    score = _score(re.split(r":", html.unescape(title))[0])
    if score:
        opp = _opponent(title)
        text = _plain(doc["title"] + " " + doc.get("body", "")[:1500])
        return score in text.replace("–", "-").replace(" - ", "-") and (not opp or opp in text or _lat(opp) in _lat(text))
    # Ο κανόνας «ίδιο πρόσωπο + κοινή λέξη» αφαιρέθηκε (19/10): έκοβε διαφορετικά άρθρα για το ίδιο πρόσωπο
    # (π.χ. «Δε μασάει από τραυματισμούς ο Ουναΐ» ≠ «Σοκ με Ουναΐ: νοκ άουτ»). Ο χρήστης θέλει να περνάνε.
    return False


def trifillakia_docs():
    """{"title", "body", "ts"} των πρόσφατων άρθρων του trifillakia.gr (ροές κατηγοριών)."""
    docs = []
    for url in TRIFILLAKIA_FEEDS:
        try:
            r = _s.get(url, timeout=30)
        except requests.RequestException:
            continue
        for item in re.findall(r"<item>(.*?)</item>", r.text, re.S):
            t = re.search(r"<title>(.*?)</title>", item, re.S)
            d = re.search(r"<description>(.*?)</description>", item, re.S)
            pd = re.search(r"<pubDate>(.*?)</pubDate>", item, re.S)
            try:
                ts = parsedate_to_datetime(pd.group(1).strip()).timestamp() if pd else 0
            except (TypeError, ValueError):
                ts = 0
            body = html.unescape(re.sub(r"<[^>]+>", " ", html.unescape(d.group(1)))) if d else ""
            docs.append({"title": html.unescape(t.group(1)) if t else "", "body": re.sub(r"\s+", " ", body), "ts": ts})
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
# Πρόσωπα του Παναθηναϊκού που φτάνουν μόνα τους στον τίτλο (δηλώσεις προπονητών χωρίς «Παναθηναϊκός»).
PAO_PEOPLE = ("ομπραντοβιτς", "νιστρουπ")


# totalbasket: κατηγορίες γυναικείου μπάσκετ και βόλεϊ → κατηγορίες του trifillakia (ονόματα όπως στο Drupal).
TB_WOMEN = {162, 229, 230, 306, 656, 1569, 1659}
TB_VOLLEY = {624}


def sport_category(source, post, title, default):
    cats = set(post.get("categories") or [])
    if source != "totalbasket.gr":
        return default
    text = _plain(title + " " + re.sub(r"<[^>]+>", " ", post["content"]["rendered"])[:600])
    if cats & TB_VOLLEY or "βολει" in text:
        return "Βόλεϊ Γυναικών" if cats & TB_WOMEN or re.search(r"γυναικ|πρασινες|αθλητρι", text) else "Βολεϊ Ανδρών"
    if cats & TB_WOMEN or re.search(r"μπασκετ γυναικ|πρασινες|wbl", text):
        return "Μπάσκετ Γυναικών"
    return default


def _is_pao_abbr(text):
    """«ΠΑΟ» ως λέξη (όχι ΠΑΟΚ)."""
    return re.search(r"(?<![a-zα-ω])παο(?![a-zα-ωκ])", _plain(text)) is not None


def about_pao(title, body, title_only=False):
    """Είδηση του Παναθηναϊκού; Ο τίτλος ή η αρχή του κειμένου (lead) πρέπει να τον αναφέρει.
    Το tag μόνο του δεν αρκεί (π.χ. «Πουλακίδας» με λάθος tag Παναθηναϊκός)."""
    if any(w in _plain(title) for w in PAO_WORDS + PAO_PEOPLE) or _is_pao_abbr(title):
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
            r = _s.get(f"{base}?{f}&per_page=20&_fields=id,date_gmt,title,link,content,featured_media,categories", timeout=40)
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
                "category": sport_category(name, p, title, category),
                "title": title,
                "link": p["link"],
                "body": p["content"]["rendered"],
                "image": drupal_image(image, f"{name}:{p['id']}"),
                "ts": ts,
            }
    return list(seen.values())


def _bmp_html(text):
    """Η βάση του trifillakia (MySQL utf8, όχι utf8mb4) δεν αποθηκεύει χαρακτήρες 4 byte (emoji, σημαίες)
    και η εισαγωγή αποτυγχάνει. Στο κείμενο γίνονται οντότητες HTML (&#128202;) που ο browser δείχνει ως emoji."""
    return "".join(c if ord(c) <= 0xFFFF else f"&#{ord(c)};" for c in text)


def _bmp_plain(text):
    """Για τον τίτλο (απλό κείμενο): τα emoji αφαιρούνται."""
    return re.sub(r"\s{2,}", " ", "".join(c for c in text if ord(c) <= 0xFFFF and c != "\ufe0f")).strip()


def _item(it):
    pub = format_datetime(datetime.fromtimestamp(it["ts"], timezone.utc))
    it = dict(it, title=_bmp_plain(it["title"]), body=_bmp_html(it["body"]))
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


def drupal_image(url, guid):
    """Φωτογραφία σε μορφή που δέχεται το Drupal. Οι WebP (συνήθεις στο totalbasket) γίνονται JPG,
    αποθηκεύονται στο docs/img και σερβίρονται από το GitHub Pages."""
    if not url or os.path.splitext(url.split("?")[0])[1].lower() in DRUPAL_IMG:
        return url
    name = re.sub(r"[^a-z0-9]+", "-", guid.lower()).strip("-") + ".jpg"
    path = os.path.join(IMG_DIR, name)
    if not os.path.exists(path):
        try:
            r = _s.get(url, timeout=40)
            im = Image.open(io.BytesIO(r.content))
            im = im.convert("RGB")
            im.thumbnail((1600, 1600))
            os.makedirs(IMG_DIR, exist_ok=True)
            im.save(path, "JPEG", quality=85, optimize=True)
        except Exception:  # noqa: BLE001
            return url
    return PAGES + "img/" + name


def _cleanup_images(items):
    """Κρατάμε μόνο τις εικόνες των άρθρων που είναι ακόμα στη ροή."""
    keep = {os.path.basename(i["image"]) for i in items if i.get("image", "").startswith(PAGES)}
    if os.path.isdir(IMG_DIR):
        for f in os.listdir(IMG_DIR):
            if f not in keep:
                os.remove(os.path.join(IMG_DIR, f))


def write_feed(items):
    _cleanup_images(items)
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
    for i in state["items"]:  # και όσα μπήκαν πριν από τη μετατροπή WebP → JPG
        i["image"] = drupal_image(i.get("image", ""), i["guid"])
    # «done»: όσα μπήκαν ποτέ στη ροή (η ροή κρατά μόνο 30), για να μην ξαναμπεί άρθρο που βγήκε από τη λίστα.
    state["done"] = list(dict.fromkeys((state.get("done") or []) + [i["guid"] for i in state["items"]]))[-400:]
    have = {i["guid"] for i in state["items"]} | set(state["blocked"]) | set(state["done"])
    candidates = []
    for src in SOURCES:
        candidates += [p for p in fetch(src, state["since"]) if p["guid"] not in have]
    if candidates:
        existing = trifillakia_docs() + [{"title": i["title"], "body": i.get("body", ""), "ts": i["ts"]} for i in state["items"]]
        # Χωρίς φωτογραφία: περιμένουμε έως 30 λεπτά (ο συντάκτης συχνά τη βάζει λίγο μετά τη δημοσίευση).
    candidates = [p for p in candidates if p["image"] or now - p["ts"] > 1800]
    for p in sorted(candidates, key=lambda p: p["ts"]):
            near = [d for d in existing if not d["ts"] or abs(d["ts"] - p["ts"]) < WINDOW]
            if any(same_story(p["title"], d) for d in near):
                log("Ροή trifillakia: υπάρχει ήδη →", p["title"])
                continue
            state["items"].append(p)
            existing.append({"title": p["title"], "body": re.sub(r"<[^>]+>", " ", p["body"]), "ts": p["ts"]})
            log("Ροή trifillakia: νέο άρθρο ←", p["source"], p["title"])
    state["items"] = sorted(state["items"], key=lambda i: -i["ts"])[:30]
    write_feed(state["items"])
    return state
