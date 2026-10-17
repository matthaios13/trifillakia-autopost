"""Ειδήσεις του trifillakia.gr (Drupal 7): εντοπισμός νέων άρθρων και στοιχεία τους.

Κάθε άρθρο έχει αύξοντα αριθμό (node id): το /node/Ν κάνει redirect στο άρθρο,
ενώ τα επόμενα νούμερα δίνουν 404 μέχρι να ανέβουν. Ένα μη δημοσιευμένο άρθρο δίνει 403.
"""
import html
import re

import requests

from .flashscore import UA

SITE = "https://www.trifillakia.gr"

# Κατηγορίες (το πρώτο κομμάτι του URL) που ανεβαίνουν στα social, με την ετικέτα της κάρτας.
SECTIONS = {
    "podosfairo": "ΠΟΔΟΣΦΑΙΡΟ",
    "mpasket": "ΜΠΑΣΚΕΤ",
    "erasitehnis": "ΕΡΑΣΙΤΕΧΝΗΣ",
    "mpasket-gynaikon": "ΜΠΑΣΚΕΤ ΓΥΝΑΙΚΩΝ",
    "polo": "ΠΟΛΟ",
    "volei-andron": "ΒΟΛΕΪ ΑΝΔΡΩΝ",
    "volei-gynaikon": "ΒΟΛΕΪ ΓΥΝΑΙΚΩΝ",
    "blogs": "BLOG",
    "prognostika-stoihimatos": "ΠΡΟΓΝΩΣΤΙΚΑ",
}
# Ό,τι δεν είναι στη λίστα δεν ανεβαίνει.

# Πόσα νούμερα μετά το τελευταίο ελέγχουμε (για κενά από διαγραμμένα / μη δημοσιευμένα άρθρα).
LOOKAHEAD = 12

_s = requests.Session()
_s.headers.update({"User-Agent": UA})


def latest_nid():
    """Ο μεγαλύτερος αριθμός άρθρου στην αρχική σελίδα."""
    try:
        r = _s.get(SITE + "/", timeout=30)
    except requests.RequestException:
        return 0
    ids = [int(x) for x in re.findall(r"/article/(\d+)/", r.text)]
    return max(ids) if ids else 0


def probe(nid):
    """'ok' + URL αν το άρθρο υπάρχει και είναι δημοσιευμένο, 'hidden' αν δεν είναι ακόμα δημόσιο, αλλιώς None."""
    try:
        r = _s.get(f"{SITE}/node/{nid}", allow_redirects=False, timeout=20)
    except requests.RequestException:
        return None, None
    if r.status_code in (301, 302) and "/article/" in r.headers.get("Location", ""):
        return "ok", r.headers["Location"]
    if r.status_code == 403:
        return "hidden", None
    return None, None


def section_of(url):
    path = url.split("trifillakia.gr", 1)[-1]
    return path.strip("/").split("/", 1)[0]


def _meta(page, prop):
    m = re.search(r'<meta (?:property|name)="%s" content="([^"]*)"' % re.escape(prop), page)
    return html.unescape(m.group(1)).strip() if m else ""


def article(nid, url):
    """Τίτλος, περίληψη, φωτογραφία, κατηγορία ενός άρθρου."""
    try:
        r = _s.get(url, timeout=30)
    except requests.RequestException:
        return None
    if r.status_code != 200:
        return None
    page = r.text
    sec = section_of(url)
    return {
        "nid": int(nid),
        "url": _meta(page, "og:url") or url,
        "title": _meta(page, "og:title"),
        "description": _meta(page, "og:description") or _meta(page, "description"),
        "image": _meta(page, "og:image"),
        "section": sec,
        "label": SECTIONS.get(sec, ""),
    }


def wanted(url):
    return section_of(url) in SECTIONS
