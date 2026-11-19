"""Ειδήσεις του trifillakia.gr (Drupal 7): εντοπισμός νέων άρθρων και στοιχεία τους.

Κάθε άρθρο έχει αύξοντα αριθμό (node id): το /node/Ν κάνει redirect στο άρθρο,
ενώ τα επόμενα νούμερα δίνουν 404 μέχρι να ανέβουν. Ένα μη δημοσιευμένο άρθρο δίνει 403.
"""
import html
import re
import time

import requests

from .flashscore import UA

SITE = "https://www.trifillakia.gr"

# Κατηγορίες (το πρώτο κομμάτι του URL) που ανεβαίνουν στα social, με την ετικέτα της κάρτας.
SECTIONS = {
    "podosfairo": "ΠΟΔΟΣΦΑΙΡΟ",
    "mpasket": "ΜΠΑΣΚΕΤ",
    "erasitehnis": "ΕΡΑΣΙΤΕΧΝΗΣ",
    "san-simera": "ΣΑΝ ΣΗΜΕΡΑ",
    "mpasket-gynaikon": "ΜΠΑΣΚΕΤ ΓΥΝΑΙΚΩΝ",
    "polo": "ΠΟΛΟ",
    "volei-andron": "ΒΟΛΕΪ ΑΝΔΡΩΝ",
    "volei-gynaikon": "ΒΟΛΕΪ ΓΥΝΑΙΚΩΝ",
    "blogs": "BLOG",
    "prognostika-stoihimatos": "ΠΡΟΓΝΩΣΤΙΚΑ",
    "gipediko": "ΓΗΠΕΔΙΚΟ",
    "podosfairo-gynaikon": "ΠΟΔΟΣΦΑΙΡΟ ΓΥΝΑΙΚΩΝ",
    "futsal-gynaikon": "FUTSAL ΓΥΝΑΙΚΩΝ",
    "futsal-andron": "FUTSAL ΑΝΔΡΩΝ",
}
# «antipaloi» (ειδήσεις αντιπάλων) σκόπιμα ΔΕΝ ανεβαίνουν στα social.
# Ό,τι δεν είναι στη λίστα δεν ανεβαίνει.

# Πόσα νούμερα μετά το τελευταίο ελέγχουμε (για κενά από διαγραμμένα / μη δημοσιευμένα άρθρα).
# Μεγάλα κενά (π.χ. 12 «καμένα» νούμερα από αποτυχημένες εισαγωγές του Feeds, 19/10) καλύπτονται ούτως ή άλλως,
# γιατί ο έλεγχος συνεχίζει μέχρι το latest_nid() των ροών. Ήταν 40: 40 σελίδες 404 χωρίς cache κάθε 5′
# βάραιναν το Drupal και καθυστερούσαν την αποθήκευση άρθρων (15/11).
LOOKAHEAD = 3  # 18/11: ήταν 8 (8 uncached 404 κάθε 5′ βάραιναν τον server)

_s = requests.Session()
_s.headers.update({"User-Agent": UA})


# 19/11: ο server του trifillakia στέλνει τα αυτόματα αιτήματα στο /node/N σε «Security Check» (από 18/11 22:38).
# Τα δημόσια RSS περνάνε κανονικά και είναι σε cache (ελαφριά), οπότε όλα τα στοιχεία των άρθρων έρχονται από εκεί:
# αριθμός (guid «N at …»), link, τίτλος, φωτογραφία και κείμενο (description), ημερομηνία.
FEED_TERMS = (1, 2, 4, 5, 299, 300, 301, 302, 5419, 5456, 5524, 5525, 5553)
FEED_URLS = [f"{SITE}/taxonomy/term/{t}/feed" for t in FEED_TERMS] + [f"{SITE}/blog/feed"]


def _text(fragment):
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment or ""))
    return re.sub(r"\s+", " ", t).strip()


def feed_items():
    """{nid: άρθρο} από όλα τα RSS (ίδια μορφή με article()). Τα αιτήματα που αποτυγχάνουν απλώς παραλείπονται."""
    out = {}
    for url in FEED_URLS:
        try:
            r = _s.get(url, timeout=30)
        except requests.RequestException:
            continue
        if r.status_code != 200 or "<rss" not in r.text[:400]:
            continue
        for item in re.findall(r"<item>(.*?)</item>", r.text, re.S):
            g = re.search(r"<guid[^>]*>\s*(\d+) at ", item)
            link = re.search(r"<link>([^<]+)</link>", item)
            if not g or not link:
                continue
            nid = int(g.group(1))
            if nid in out:
                continue
            title = html.unescape(re.search(r"<title>(.*?)</title>", item, re.S).group(1)).strip()
            desc = html.unescape((re.search(r"<description>(.*?)</description>", item, re.S) or [None, ""])[1] or "")
            img = re.search(r'field-name-field-image.*?<img[^>]+src="([^"]+)"', desc, re.S)
            thumb = html.unescape(img.group(1)) if img else ""
            image = re.sub(r"/styles/[^/]+/public/", "/", thumb).split("?", 1)[0] if thumb else ""
            body = re.search(r'field-name-body.*?<div class="field-item[^"]*">(.*?)</div>\s*</div>\s*</div>', desc, re.S)
            text = _text(body.group(1) if body else "")
            if len(text) > 300:
                text = text[:300].rsplit(" ", 1)[0] + "…"
            link_url = link.group(1).strip()
            sec = section_of(link_url)
            out[nid] = {"nid": nid, "url": link_url, "title": title, "description": text, "image": image,
                        "thumb": thumb, "section": sec, "label": SECTIONS.get(sec, "")}
    return out


def latest_nid():
    """Ο μεγαλύτερος αριθμός άρθρου στην αρχική και στις ροές των κατηγοριών (η αρχική μπορεί να είναι σε cache)."""
    ids = []
    # 18/11: ΧΩΡΙΣ «nc» και χωρίς την αρχική: τα uncached render (αρχική ~5″) κάθε 5′ γέμιζαν το shared hosting.
    # Η cache σελίδων καθαρίζει σε κάθε αποθήκευση άρθρου (κανόνας Rules), άρα οι ροές είναι φρέσκιες.
    for url in [f"{SITE}/taxonomy/term/{t}/feed" for t in (1, 2, 4, 5, 302, 5419, 5456, 5524, 5525, 5553)]:
        try:
            r = _s.get(url, timeout=30)
        except requests.RequestException:
            continue
        ids += [int(x) for x in re.findall(r"/article/(\d+)/", r.text)]
    return max(ids) if ids else 0


LAST_MISS = {}


def probe(nid):
    """'ok' + URL αν το άρθρο υπάρχει και είναι δημοσιευμένο, 'hidden' αν δεν είναι ακόμα δημόσιο, αλλιώς None."""
    try:
        # Με «?nc=…» παρακάμπτουμε την cache του site, που κρατά το 404 ενός νούμερου έως 1 ώρα.
        r = _s.get(f"{SITE}/node/{nid}", params={"nc": int(time.time())}, allow_redirects=False, timeout=20)
    except requests.RequestException:
        return "error", None  # timeout/σύνδεση: ΔΕΝ σημαίνει ότι δεν υπάρχει (17/11: χάθηκε το 25053 σε 524)
    if r.status_code >= 500:
        return "error", None
    if r.status_code in (301, 302) and "/article/" in r.headers.get("Location", ""):
        return "ok", r.headers["Location"].split("?", 1)[0]
    if r.status_code == 403:
        return "hidden", None
    LAST_MISS[nid] = f"{r.status_code} {r.headers.get('Location', '')[:80]} {r.headers.get('cf-cache-status', '')} {r.headers.get('server', '')}"
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


_home_html = {}


def thumb_url(image):
    """Μικρό αντίγραφο (320x320) της φωτογραφίας, με το κλειδί itok που θέλει το Drupal για νέες φωτογραφίες.

    Το παίρνουμε από την αρχική σελίδα· αν δεν υπάρχει εκεί, η κανονική φωτογραφία.
    """
    if not image or "/field/image/" not in image:
        return image
    name = image.split("/field/image/", 1)[1]
    if "page" not in _home_html:
        try:
            _home_html["page"] = _s.get(SITE + "/", timeout=30).text
        except requests.RequestException:
            _home_html["page"] = ""
    m = re.search(r'/sites/default/files/styles/image_320x320/public/field/image/%s\?itok=[\w-]+' % re.escape(name), _home_html["page"])
    return SITE + html.unescape(m.group(0)) if m else image
