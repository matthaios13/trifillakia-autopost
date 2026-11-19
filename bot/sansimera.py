"""«Σαν σήμερα» του panathinaikanea.gr → trifillakia.gr, μία φορά τη μέρα (19/11).

Το panathinaikanea βγάζει κάθε πρωί (~06:15) ένα άρθρο τύπου pn_history με slug san-simera-YYYY-MM-DD.
Το παίρνουμε από το REST, μετατρέπουμε τα βίντεο (στο panathinaikanea παίζουν με JS) σε YouTube iframe
και το δίνουμε στη ροή CSV όπως τα υπόλοιπα άρθρα. Κατηγορία «Σαν σήμερα» (tid 5553).
"""
import html
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from .flashscore import UA

API = "https://panathinaikanea.gr/wp-json/wp/v2"
TZ = ZoneInfo("Europe/Athens")
FROM_HOUR = 6  # πριν από τις 06:00 δεν έχει βγει ακόμα
CATEGORY = "Σαν σήμερα"  # κατηγορία tid 5553, /san-simera (19/11)

_s = requests.Session()
_s.headers.update({"User-Agent": UA})


def _video(m):
    yid = m.group(1)
    title = re.search(r'class="pn-hist-video__title">(.*?)</p>', m.group(0), re.S)
    cap = f"<p><em>{title.group(1)}</em></p>" if title else ""
    return (f'<p><iframe width="100%" height="450" src="https://www.youtube.com/embed/{yid}" frameborder="0" '
            f'allow="accelerometer; autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe></p>{cap}')


def clean(content):
    c = re.sub(r'<div class="pn-hist-video"[^>]*data-yt="([\w-]{6,20})".*?</div>', _video, content, flags=re.S)
    c = re.sub(r"<button\b.*?</button>", "", c, flags=re.S)
    c = re.sub(r"<script\b.*?</script>", "", c, flags=re.S)
    c = re.sub(r'\s(id|class|data-[\w-]+|scope|decoding|loading)="[^"]*"', "", c)
    return c.strip()


def events(content):
    """[{"year", "label", "yt"}] για κάθε γεγονός (h2/h3 id="otd-…"), με τη σειρά του άρθρου (πρώτο = κύριο)."""
    out = []
    heads = list(re.finditer(r'<h[23] id="otd-(\d{4})-\d\d-\d\d-([a-z])">(.*?)</h[23]>', content, re.S))
    for n, m in enumerate(heads):
        part = content[m.end(): heads[n + 1].start() if n + 1 < len(heads) else len(content)]
        yt = re.search(r'data-yt="([\w-]{6,20})"', part)
        full = html.unescape(re.sub(r"<[^>]+>", "", m.group(3))).split("·", 1)[-1].strip()
        out.append({"year": int(m.group(1)), "sport": m.group(2), "full": full,
                    "label": full.replace("Παναθηναϊκός", "ΠΑΟ"), "yt": yt.group(1) if yt else None})
    return out


MONTHS_GEN = ["ιανουαριου", "φεβρουαριου", "μαρτιου", "απριλιου", "μαιου", "ιουνιου", "ιουλιου", "αυγουστου",
              "σεπτεμβριου", "οκτωβριου", "νοεμβριου", "δεκεμβριου"]


def events_for_title(title):
    """(γεγονότα, μέρα, μήνας) από τίτλο «Σαν σήμερα, 19 Νοεμβρίου: …» (για τις κάρτες Instagram)."""
    import unicodedata
    t = "".join(c for c in unicodedata.normalize("NFD", title.lower()) if unicodedata.category(c) != "Mn")
    m = re.search(r"σαν σημερα,?\s+(\d{1,2})\s+([α-ω]+)", t)
    if not m or m.group(2) not in MONTHS_GEN:
        return None
    day, month = int(m.group(1)), MONTHS_GEN.index(m.group(2)) + 1
    year = datetime.now(TZ).year
    try:
        r = _s.get(f"{API}/pn_history", params={"slug": f"san-simera-{year}-{month:02d}-{day:02d}", "_fields": "content"}, timeout=30)
        posts = r.json() if r.status_code == 200 else []
    except (requests.RequestException, ValueError):
        return None
    return (events(posts[0]["content"]["rendered"]), day, month) if posts else None


def candidate(done, log=print, now=None):
    """Το σημερινό «Σαν σήμερα» ως άρθρο για τη ροή, ή None (δεν βγήκε ακόμα / το πήραμε ήδη)."""
    today = datetime.now(TZ) if now is None else datetime.fromtimestamp(now, TZ)
    if today.hour < FROM_HOUR:
        return None
    slug = f"san-simera-{today:%Y-%m-%d}"
    guid = f"panathinaikanea.gr:{slug}"
    if guid in done:
        return None
    try:
        r = _s.get(f"{API}/pn_history", params={"slug": slug, "_fields": "id,date_gmt,title,excerpt,content,featured_media,link"}, timeout=30)
        posts = r.json() if r.status_code == 200 else []
    except (requests.RequestException, ValueError) as e:
        log("Σαν σήμερα: σφάλμα", repr(e)[:120])
        return None
    if not posts:
        return None
    p = posts[0]
    image = ""
    if p.get("featured_media"):
        try:
            m = _s.get(f"{API}/media/{p['featured_media']}", params={"_fields": "source_url"}, timeout=30).json()
            image = m.get("source_url", "")
        except (requests.RequestException, ValueError):
            pass
    content = p["content"]["rendered"]
    sub = html.unescape(re.sub(r"<[^>]+>", "", p["excerpt"]["rendered"])).strip()
    ts = datetime.fromisoformat(p["date_gmt"] + "+00:00").timestamp()
    return {
        "guid": guid,
        "title": html.unescape(p["title"]["rendered"]),
        "body": clean(content),
        "subtitle": sub,
        "category": CATEGORY,
        "tags": ["Σαν σήμερα", "Ιστορία"],
        "image": image,
        "ts": ts,
        "link": p["link"],
        "source": "panathinaikanea.gr",
        "feature": False,
        "events": events(content),
        "day": today.day,
        "month": today.month,
    }
