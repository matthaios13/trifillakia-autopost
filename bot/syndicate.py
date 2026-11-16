"""Άρθρα για τον Παναθηναϊκό από bala24.gr (ποδόσφαιρο) και totalbasket.gr (μπάσκετ) → trifillakia.gr.

Το trifillakia.gr (Drupal 7) έχει CAPTCHA στο login, οπότε δεν γράφουμε απευθείας: φτιάχνουμε ένα RSS
(docs/pao-feed.xml στο GitHub Pages) και το module Feeds του Drupal το τραβάει και δημιουργεί τα άρθρα
(importer «pao_news», ίδια λογική με τον «ELABET άρθρα»).

Ένα άρθρο μπαίνει μόνο αν δεν υπάρχει ήδη στο trifillakia.gr με παρόμοιο τίτλο.
"""
import csv
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
from . import pao1908

FEED = os.path.join(ROOT, "docs", "pao-feed.xml")
CSV_FEED = os.path.join(ROOT, "docs", "pao-feed.csv")  # importer «PAO news CSV»: υπότιτλος + ετικέτες (από 13/11)
IMG_DIR = os.path.join(ROOT, "docs", "img")
PAGES = "https://matthaios13.github.io/trifillakia-autopost/"

SOURCES = [
    # (όνομα, βάση REST, φίλτρα, κατηγορία στο trifillakia, συντάκτης)
    ("bala24.gr", "https://bala24.gr/wp-json/wp/v2/posts", ["categories=55", "tags=47"], "Ποδοσφαιρο"),
    ("totalbasket.gr", "https://totalbasket.gr/wp-json/wp/v2/posts", ["tags=137"], "Μπασκετ"),
]
TRIFILLAKIA_FEEDS = [f"https://www.trifillakia.gr/taxonomy/term/{t}/feed" for t in (1, 2, 4, 5, 299, 300, 301, 302, 5456, 5496)]

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


MARKERS = ("γυναικ", "βολει", "μπασκετ", "πολο", "χαντμπολ", "νεων", "κ19", "κ17")


def _markers(text):
    t = _plain(text)
    return {m for m in MARKERS if m in t}


GENERIC = ("γυναικ", "ανδρ", "εθνικ", "λεωφορ", "κυριακ", "δευτερ", "τριτη", "τεταρτ", "πεμπτ", "παρασκ", "σαββατ",
           "ιανουα", "φεβρου", "μαρτι", "απριλ", "μαιου", "ιουνι", "ιουλι", "αυγουσ", "σεπτεμ", "οκτωβρ", "νοεμβρ",
           "δεκεμβ", "πρωταθ", "αγωνισ", "ομαδα", "σεζον", "league", "stoix", "volley")


def _body_names(text):
    """Κύρια ονόματα (κεφαλαίο αρχικό, ≥5 γράμματα), χωρίς ομάδες/ΠΑΟ: «Σιαφαρίκα», «Αντρέεφσκα»."""
    out = set()
    for w in re.findall(r"(?<![\w])[Α-ΩΆ-ΏA-Z][^\W\d_]{4,}", text):
        k = _plain(w)
        if k not in STOP and not k.startswith(GENERIC) and not k[:5].startswith(TEAMS) and not any(x in k for x in PAO_WORDS):
            out.add(k[:6])
    return out


RESULT_RE = re.compile(r"νικ|ηττ|επικρατ|ισοπαλ|εχασε|λυγισε|υπεταξε|κερδισε|απωλει|βαθμο|προκρι|αποκλει")


def same_story(title, doc, body=""):
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
    # Ρεπορτάζ αγώνα χωρίς σκορ στον τίτλο («Ο ΠΑΟΚ νίκησε τον Παναθηναϊκό…» ↔ «Πρώτη ήττα της σεζόν…»):
    # ίδιος αντίπαλος, ίδιο άθλημα/φύλο και τουλάχιστον 3 κοινά ονόματα (παίκτριες/σκόρερ) στα κείμενα (15/11).
    if not score and body and RESULT_RE.search(_plain(title)):
        mine = html.unescape(re.sub(r"<[^>]+>", " ", body))[:2500]
        other = doc["title"] + " " + doc.get("body", "")[:2500]
        opp = _opponent(title)
        if (opp and opp.startswith(TEAMS) and _markers(title + " " + mine[:400]) == _markers(other[:500])
                and opp in _plain(other) and "elabet" not in _plain(title + other[:80])
                and RESULT_RE.search(_plain(other[:600])) and len(_body_names(mine) & _body_names(other)) >= 3):
            return True
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


def _og_image(link):
    """Η φωτογραφία από τη σελίδα του άρθρου (og:image), όταν το REST δεν δίνει το media
    (π.χ. 401 για φωτογραφία που ξαναχρησιμοποιήθηκε από παλιότερο άρθρο)."""
    if not link:
        return ""
    try:
        r = _s.get(link, timeout=30)
        m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', r.text) if r.status_code == 200 else None
        return html.unescape(m.group(1)) if m else ""
    except requests.RequestException:
        return ""


PAO = "Παναθηναϊκ"
ORIGIN_RE = re.compile(r"/pao-\d{4,6}(?:-\d+)?(?:-\d+x\d+)?\.(?:jpe?g|png|webp)", re.I)


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
    if source == "bala24.gr":
        # γυναικείο ποδόσφαιρο του Παναθηναϊκού → δικό του τμήμα στο trifillakia
        t = _plain(title)
        if re.search(r"γυναικ|ποδοσφαιριστρι|women", t):
            return "Ποδόσφαιρο Γυναικών"
        return default
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


YOUTH_RE = re.compile(r"(?<![a-zα-ω])(κ|u)-?1[0-9](?![0-9])|νεων|ακαδημ|εφηβ|παιδ|παμπαιδ|κορασ|γυναικ|πρασινες|βολει|πολο|futsal|χαντμπολ")


def slider_ok(category, title, tags=(), known=()):
    """«Appear on Slider?» για άρθρα bala24/totalbasket (15/11, κανόνας χρήστη): ΜΟΝΟ Παναθηναϊκός,
    ποδόσφαιρο ανδρών και μπάσκετ ανδρών, και η είδηση να αφορά τον Παναθηναϊκό, όχι αντίπαλο
    (π.χ. «Σπανούλης: …δύσκολο να κερδίσεις Ολυμπιακό και Παναθηναϊκό» = όχι)."""
    if category not in ("Ποδοσφαιρο", "Μπασκετ"):
        return False
    t = _plain(title)
    if YOUTH_RE.search(t):
        return False
    def pao_at(x):
        hits = [x.find(w) for w in PAO_WORDS + PAO_PEOPLE if w in x]
        m = re.search(r"(?<![a-zα-ω])παο(?![a-zα-ωκ])", x)
        if m:
            hits.append(m.start())
        return min(hits) if hits else -1
    head = t.split(":", 1)[0] if ":" in t[:90] else ""
    is_match = re.search(r"\s[-–]\s", head or t[:60]) is not None
    # «Σπανούλης: …» / «Μπαρτσελόνα: …»: ο τίτλος ξεκινά με άλλον (δηλώσεις/νέα αντιπάλου)
    # Δηλώσεις «Πελίστρι: …» περνάνε μόνο αν το άρθρο έχει ετικέτα Παναθηναϊκός και καμία άλλης ομάδας/διεθνή.
    tg = [_plain(x) for x in tags]
    pao_tag = any(any(w in x for w in PAO_WORDS) and "ακαδημ" not in x for x in tg)
    other_tag = any((x[:5].startswith(TEAMS) and x not in ("super league", "stoiximan super league", "euroleague", "basket league"))
                    or "διεθν" in x or x.startswith("εθνικη ") for x in tg if not any(w in x for w in PAO_WORDS))
    pos = pao_at(t)
    if pos < 0:
        # «Ναν: «Φυσικά και είμαι κουρασμένος…»»: δήλωση παίκτη του ΠΑΟ χωρίς το όνομα της ομάδας στον τίτλο
        return bool(head) and ((pao_tag and not other_tag) or _plain(head)[:6] in known)
    if head and pao_at(head) < 0 and not is_match and not (pao_tag and not other_tag) and _plain(head)[:6] not in known:
        return False
    # «Ο Ολυμπιακός νίκησε τον Παναθηναϊκό…»: πρώτα αντίπαλος στον τίτλο, όχι αγώνας «Χ – Παναθηναϊκός»
    words = re.findall(r"(?<![0-9a-zα-ω])[a-zα-ω]+", t[:pos])
    if not is_match and any(w[:5].startswith(TEAMS) and w not in ("super", "league", "euroleague", "stoiximan", "gbl")
                            for w in words):
        return False
    return True


def is_opponent(category, title, tags=(), known=()):
    """Είδηση αντιπάλου → κατηγορία «Αντίπαλοι» (16/11, κανόνας χρήστη): «ΟΦΗ: …ενόψει Παναθηναϊκού»,
    «Σπανούλης: …». Δηλώσεις/νέα δικών μας (ετικέτα Παναθηναϊκός χωρίς άλλη ομάδα) μένουν στην ενότητά τους."""
    if category not in ("Ποδοσφαιρο", "Μπασκετ"):
        return False
    t = _plain(title)
    if YOUTH_RE.search(t):
        return False
    tg = [_plain(x) for x in tags]
    pao_tag = any(any(w in x for w in PAO_WORDS) and "ακαδημ" not in x for x in tg)
    has_pao = any(w in t for w in PAO_WORDS + PAO_PEOPLE) or _is_pao_abbr(title)
    head = t.split(":", 1)[0] if ":" in t[:90] else ""
    is_match = re.search(r"\s[-–]\s", head or t[:60]) is not None
    # γνωστό πρόσωπο του Παναθηναϊκού (από άλλα άρθρα με ετικέτα ΠΑΟ), π.χ. «Γιαμπουσέλε: …» χωρίς ετικέτα ΠΑΟ
    if known and (_plain(head)[:6] in known if head else False):
        return False
    if known and not has_pao and not pao_tag and _body_names(title) & set(known):
        return False
    if not has_pao and not pao_tag:
        return True
    if head and not is_match and not any(w in head for w in PAO_WORDS + PAO_PEOPLE) and not _is_pao_abbr(head):
        first = re.findall(r"[a-zα-ω]+", head)
        head_is_team = bool(first) and first[0][:5].startswith(TEAMS) and first[0] not in ("super", "league", "euroleague", "stoiximan", "gbl")
        if head_is_team or not pao_tag:
            return True
    return False


def pao_people(items):
    """Πρόσωπα του Παναθηναϊκού (ρίζες 6 γραμμάτων) από άρθρα με ετικέτα Παναθηναϊκός: ετικέτες-πρόσωπα
    («Γκερσόν Γιαμπουσέλε» → «γιαμπου») και ονόματα στον τίτλο («Εκτός οι Γιαμπουσέλε, Σλούκας και Ναν»)."""
    out = set()
    for it in items:
        base, ids = it.get("base"), it.get("tag_ids") or []
        if not base or not ids:
            continue
        tag_names(base, ids)
        names = [_tag_cache.get((base, i), "") for i in ids]
        if not any(any(w in _plain(n) for w in PAO_WORDS) for n in names):
            continue
        for n in names:
            k = _plain(n)
            words = k.split()
            if (len(words) in (2, 3) and not any(w in k for w in PAO_WORDS) and not words[0][:5].startswith(TEAMS)
                    and not k.startswith(GENERIC) and not re.search(r"\d|league|euro|cup|κυπελλ|πρωταθλ|εθνικ", k)):
                out.add(words[-1][:6])
        # ονόματα μέσα στη φράση (όχι η πρώτη λέξη του τίτλου ή μετά την «:», που έχει πάντα κεφαλαίο)
        t = it.get("title", "")
        first = {_plain(w)[:6] for w in re.findall(r"(?:^|[:«\-–]\s*)([^\W\d_]+)", t)}
        out |= _body_names(t) - first
    return out


def fetch(source, since_ts, log=None):
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
            r = _s.get(f"{base}?{f}&per_page=20&_fields=id,date_gmt,title,link,content,featured_media,categories,tags", timeout=40)
            posts = r.json() if r.status_code == 200 else []
            if r.status_code != 200 and log:
                log(f"Ροή trifillakia: {name} απάντησε {r.status_code} ({f.split('=')[0]})", r.text[:150].replace("\n", " "))
        except (requests.RequestException, ValueError) as e:
            posts = []
            if log:
                log(f"Ροή trifillakia: σφάλμα {name} ({f.split('=')[0]})", repr(e)[:150])
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
            if not image and p.get("featured_media"):
                image = _og_image(p["link"])
            if ORIGIN_RE.search(image or ""):  # ήρθε από το trifillakia: όχι πίσω (ούτε μετατροπή φωτογραφίας)
                seen[f"{name}:{p['id']}"] = {"guid": f"{name}:{p['id']}", "title": title, "image": "", "image_src": image, "ts": ts}
                continue
            seen[f"{name}:{p['id']}"] = {
                "guid": f"{name}:{p['id']}",
                "source": name,
                "category": sport_category(name, p, title, category),
                "title": title,
                "link": p["link"],
                "body": p["content"]["rendered"],
                "image": drupal_image(image, f"{name}:{p['id']}"),
                "ts": ts,
                "tag_ids": p.get("tags") or [],
                "base": base,
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
    """Φωτογραφία σε μορφή που δέχεται το Drupal. Ό,τι δεν είναι ήδη JPG (WebP, PNG, GIF) γίνεται JPG,
    αποθηκεύεται στο docs/img και σερβίρεται από το GitHub Pages. Οι PNG (συνήθως screenshots) είναι πολύ
    βαριές για το κεντρικό slider του trifillakia (1170x660)."""
    # JPG με ελληνικά ή κενά στο όνομα (π.χ. «Generic Πρόγραμμα ΑΟ - Copy.jpg» του pao1908) το Drupal δεν τα
    # κατεβάζει: άρθρο χωρίς φωτογραφία (16/11). Αυτά περνούν κι αυτά από το docs/img.
    plain = url.isascii() and " " not in url if url else True
    if not url or (plain and os.path.splitext(url.split("?")[0])[1].lower() in (".jpg", ".jpeg")):
        return url
    name = re.sub(r"[^a-z0-9]+", "-", guid.lower()).strip("-") + ".jpg"
    path = os.path.join(IMG_DIR, name)
    if not os.path.exists(path):
        try:
            r = _s.get(requests.utils.requote_uri(url), timeout=40)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content))
            if im.mode in ("RGBA", "LA", "P"):
                im = im.convert("RGBA")
                bg = Image.new("RGB", im.size, (255, 255, 255))
                bg.paste(im, mask=im.split()[3])
                im = bg
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


# Ετικέτες του bala24/totalbasket που είναι εσωτερικές (θέσεις στην αρχική κ.λπ.), όχι θέματα.
SKIP_TAGS = {"top", "2ndtop", "3rdtop", "hot", "main", "slider", "featured", "breaking", "διεθνη", "bala", "bala24", "totalbasket"}
_tag_cache = {}


def tag_names(base, ids):
    """Ονόματα ετικετών (έως 5), χωρίς τις εσωτερικές."""
    ids = [i for i in ids if (base, i) not in _tag_cache]
    if ids:
        try:
            r = _s.get(base.replace("/posts", "/tags"), params={"include": ",".join(map(str, ids)), "per_page": 100, "_fields": "id,name"}, timeout=30)
            for t in r.json() if r.status_code == 200 else []:
                _tag_cache[(base, t["id"])] = html.unescape(t["name"]).strip()
        except (requests.RequestException, ValueError):
            pass
    return None


def post_tags(base, ids):
    tag_names(base, ids)
    out = []
    for i in ids:
        n = _tag_cache.get((base, i), "")
        if n and _plain(n) not in SKIP_TAGS and n not in out:
            out.append(n)
    return out[:5]


def subtitle(link):
    """Ο υπότιτλος (tagline του Foxiz: <h2 class="s-tagline">) από τη σελίδα του άρθρου."""
    try:
        r = _s.get(link, timeout=30)
    except requests.RequestException:
        return ""
    m = re.search(r'<h2[^>]*class="[^"]*s-tagline[^"]*"[^>]*>(.*?)</h2>', r.text, re.S) if r.status_code == 200 else None
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", m.group(1)))).strip() if m else ""


def _lead_sentence(body, limit=220):
    """Η πρώτη πρόταση του κειμένου (για υπότιτλο όταν δεν υπάρχει)."""
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body or ""))).strip()
    m = re.match(r"(.{40,%d}?[.!;»])(\s|$)" % limit, text)
    return (m.group(1) if m else text[:limit].rsplit(" ", 1)[0] + "…") if text else ""


def make_subtitle(title, body, log=print):
    """Υπότιτλος όταν η πηγή δεν έχει (π.χ. κάποια άρθρα του totalbasket): μία πρόταση από το Claude,
    αλλιώς η πρώτη πρόταση του κειμένου (16/11, κανόνας χρήστη: κάθε άρθρο με υπότιτλο)."""
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    lead = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body or ""))).strip()[:2500]
    if key and lead:
        prompt = ("Γράψε υπότιτλο για αθλητικό άρθρο του trifillakia.gr (Παναθηναϊκός): ΜΙΑ πρόταση στα ελληνικά, "
                  "έως 200 χαρακτήρες, που συμπληρώνει τον τίτλο με το βασικό στοιχείο της είδησης, χωρίς να τον "
                  "επαναλαμβάνει και χωρίς να επινοεί στοιχεία. Απάντησε ΜΟΝΟ με τον υπότιτλο.\n\n"
                  f"Τίτλος: {title}\nΚείμενο: {lead}")
        try:
            r = requests.post("https://api.anthropic.com/v1/messages", timeout=60, headers={
                "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": "claude-sonnet-5-5", "max_tokens": 300, "messages": [{"role": "user", "content": prompt}]})
            if r.status_code == 200:
                txt = "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")
                txt = re.sub(r"\s+", " ", txt).strip().strip('"«»')
                if 30 <= len(txt) <= 260 and _plain(txt) != _plain(title):
                    return txt
            else:
                log(f"Ροή trifillakia: υπότιτλος Claude {r.status_code}", r.text[:120].replace("\n", " "))
        except requests.RequestException as e:
            log("Ροή trifillakia: σφάλμα υπότιτλου", repr(e)[:120])
    return _lead_sentence(body)


def write_csv(items):
    """Ροή CSV για το importer «PAO news CSV»: ξεχωριστές στήλες για υπότιτλο (body:summary), ετικέτες, τμήμα."""
    # Ονόματα στηλών = πηγές του mapping (κλώνος του «PAO news»): description→body, source:url→εικόνα κ.λπ.
    cols = ["guid", "title", "description", "summary", "category", "tag1", "tag2", "tag3", "tag4", "tag5",
            "source:url", "timestamp", "source:title", "url", "author_name", "feature"]
    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_ALL, lineterminator="\n")
    w.writerow(cols)
    for it in sorted(items, key=lambda i: -i["ts"]):
        tags = [_bmp_plain(t) for t in (it.get("tags") or [])][:5]
        w.writerow([
            it["guid"], _bmp_plain(it["title"]), _bmp_html(it["body"]).replace("\r", " ").replace("\n", " "),
            _bmp_plain(it.get("subtitle") or ""), it["category"], *(tags + [""] * (5 - len(tags))),
            it.get("image") or "", int(it["ts"]), "fa-file-text", it["link"], it["source"],
            "yes" if it.get("feature") else "no",
        ])
    data = buf.getvalue()
    try:
        with open(CSV_FEED, encoding="utf-8") as fh:
            if fh.read() == data:
                return False
    except OSError:
        pass
    with open(CSV_FEED, "w", encoding="utf-8") as fh:
        fh.write(data)
    return True


def write_feed(items):
    os.makedirs(os.path.dirname(FEED), exist_ok=True)
    xml = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<rss version="2.0"><channel>'
        "<title>Trifillakia – Παναθηναϊκός από bala24 / totalbasket / pao1908</title>"
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
        if not i.get("image") and now - i["ts"] < 2 * 86400:
            i["image"] = _og_image(i.get("link", ""))  # άρθρο που μπήκε χωρίς φωτογραφία
        i["image"] = drupal_image(i.get("image", ""), i["guid"])
    # «done»: όσα μπήκαν ποτέ στη ροή (η ροή κρατά μόνο 30), για να μην ξαναμπεί άρθρο που βγήκε από τη λίστα.
    state["done"] = list(dict.fromkeys((state.get("done") or []) + [i["guid"] for i in state["items"]]))[-400:]
    have = {i["guid"] for i in state["items"]} | set(state["blocked"]) | set(state["done"])
    candidates = []
    known = set(state.get("pao_people") or [])
    for src in SOURCES:
        got = fetch(src, state["since"], log)
        known |= pao_people(got)
        log(f"Ροή trifillakia: {src[0]} {len(got)} άρθρα, νέα {sum(p['guid'] not in have for p in got)}")
        candidates += [p for p in got if p["guid"] not in have]
    state["pao_people"] = sorted(known)[-600:]
    if candidates:
        # Συγκρίνουμε ΜΟΝΟ με όσα έγραψαν οι συντάκτες του trifillakia: άρθρα που ήρθαν από bala24/totalbasket
        # δεν «κόβουν» άλλα άρθρα των ίδιων site (δύο άρθρα του bala24 = δύο ειδήσεις).
        # Συγκρίνουμε με ΟΛΑ τα άρθρα του trifillakia (συντάκτες, pao1908, άλλη πηγή), εκτός από όσα ήρθαν από την
        # ΙΔΙΑ πηγή: δύο άρθρα του bala24 = δύο ειδήσεις, αλλά bala24 μετά από pao1908/συντάκτη = ίδια είδηση (15/11).
        by_src = {}
        for i in state["items"]:
            by_src.setdefault(i.get("source", ""), set()).add(_plain(_bmp_plain(i["title"])))
        existing = trifillakia_docs()
        # Χωρίς φωτογραφία: περιμένουμε έως 30 λεπτά (ο συντάκτης συχνά τη βάζει λίγο μετά τη δημοσίευση).
    # Άρθρα που πήρε το totalbasket/bala24 ΑΠΟ το trifillakia (φωτογραφία «pao-<nid>.jpg») δεν ξαναγυρίζουν
    # εδώ με άλλον τίτλο (13/11: Γιαννακόπουλος 24940→24955, ΠΑΟ–Μπαρτσελόνα 24938→24956).
    for p in [p for p in candidates if ORIGIN_RE.search(p.get("image_src") or p.get("image") or "")]:
        log("Ροή trifillakia: προέρχεται από το trifillakia →", p["title"])
        state["done"].append(p["guid"])
    candidates = [p for p in candidates if not ORIGIN_RE.search(p.get("image_src") or p.get("image") or "")]
    candidates = [p for p in candidates if p["image"] or now - p["ts"] > 1800]
    for p in sorted(candidates, key=lambda p: p["ts"]):
            mine = by_src.get(p.get("source", ""), set())
            near = [d for d in existing if (not d["ts"] or abs(d["ts"] - p["ts"]) < WINDOW)
                    and _plain(_bmp_plain(d["title"])) not in mine]
            if any(same_story(p["title"], d, p.get("body", "")) for d in near):
                log("Ροή trifillakia: υπάρχει ήδη →", p["title"])
                continue
            p["subtitle"] = subtitle(p["link"]) or make_subtitle(p["title"], p.get("body", ""), log)
            base, ids = p.pop("base", ""), p.pop("tag_ids", [])
            p["tags"] = post_tags(base, ids)
            names = [_tag_cache.get((base, i), "") for i in ids]
            if is_opponent(p["category"], p["title"], names, known):
                p["category"] = "Αντίπαλοι"
            p["feature"] = slider_ok(p["category"], p["title"], names, known)
            p["added"] = now
            state["items"].append(p)
            state["done_titles"] = (state.get("done_titles") or [])[-399:] + [_bmp_plain(p["title"])]
            log("Ροή trifillakia: νέο άρθρο ←", p["source"], p["title"], "| υπότιτλος:", bool(p["subtitle"]), "| ετικέτες:", ", ".join(p["tags"]))
    # Ερασιτέχνης: pao1908.com, ξαναγραμμένα (έως 5 ανά εκτέλεση, ώστε το backfill από 1/11 να μπαίνει σταδιακά).
    try:
        ours = {_plain(t) for t in state.get("done_titles", [])} | {_plain(i["title"]) for i in state["items"]}
        docs = [d for d in trifillakia_docs() if _plain(_bmp_plain(d["title"])) not in ours]
        fails = state.setdefault("pao_fail", {})
        for p in pao1908.candidates(have, docs, same_story, log, fails):
            if p.get("skip"):
                state["done"].append(p["guid"])
                continue
            p["image"] = drupal_image(p["image"], p["guid"])
            p["added"] = now
            state["items"].append(p)
            state["done"].append(p["guid"])
            state["done_titles"] = (state.get("done_titles") or [])[-399:] + [_bmp_plain(p["title"])]
            log("Ροή trifillakia: νέο άρθρο ←", p["source"], p["title"])
        state["pao_fail"] = dict(list(fails.items())[-50:])
    except Exception as e:  # noqa: BLE001
        log("Σφάλμα ροής pao1908", repr(e)[:200])
    for i in state["items"]:  # και όσα μπήκαν ήδη με τέτοια εικόνα (ελληνικά/κενά στο όνομα)
        if i.get("image") and not i["image"].startswith(PAGES):
            i["image"] = drupal_image(i["image"], i["guid"])
    # Τα 30 πιο πρόσφατα + όσα μπήκαν τις τελευταίες 6 ώρες (παλιά άρθρα του backfill, μέχρι να τα πάρει το Drupal).
    newest = sorted(state["items"], key=lambda i: -i["ts"])
    recent = {i["guid"] for i in newest if now - i.get("added", 0) < 6 * 3600}
    state["items"] = [i for n, i in enumerate(newest) if n < 30 or i["guid"] in recent]
    # Από 13/11 τα νέα άρθρα πάνε στη ροή CSV (υπότιτλος + ετικέτες). Η XML κρατά μόνο όσα είχε ήδη, ώστε το
    # παλιό importer να μη φέρει τίποτα νέο και κανένα άρθρο να μη μπει δύο φορές (κάθε importer έχει δικά του GUID).
    if "xml_done" not in state:
        state["xml_done"] = list(dict.fromkeys(state.get("done", []) + [i["guid"] for i in state["items"]]))
    old = set(state["xml_done"])
    state["xml_done"] = [g for g in state["xml_done"] if g in {i["guid"] for i in state["items"]}]  # μόνο όσα είναι ακόμα στη ροή
    # Όσα μπήκαν ήδη στο site βγαίνουν από τη ροή CSV: αλλιώς, αν ο συντάκτης σβήσει το άρθρο, το Feeds
    # «ξεχνά» ότι το έφερε και το ξαναφέρνει (15/11: ΠΑΟΚ–Παναθηναϊκός γυναικών σβήστηκε 2 φορές και ξαναγύρισε).
    try:
        on_site = {_plain(_bmp_plain(d["title"])) for d in trifillakia_docs()}
    except Exception:  # noqa: BLE001
        on_site = set()
    for i in state["items"]:
        if not i.get("imported") and (_plain(_bmp_plain(i["title"])) in on_site or now - i.get("added", i["ts"]) > 3 * 3600):
            i["imported"] = now
    write_feed([i for i in state["items"] if i["guid"] in old])
    write_csv([i for i in state["items"] if i["guid"] not in old and not i.get("imported")])
    _cleanup_images(state["items"])
    return state
