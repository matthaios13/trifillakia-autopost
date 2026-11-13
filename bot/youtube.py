"""Προγραμματισμένες εκπομπές του καναλιού Trifillakia στο YouTube (@trifillakia_gr).

Χωρίς κλειδί API: η ροή RSS της λίστας «ζωντανά» του καναλιού (UULV…) δείχνει και τις
προγραμματισμένες εκπομπές μόλις οριστούν, και η σελίδα του βίντεο έχει «isUpcoming» και
την ώρα έναρξης («scheduledStartTime»).
"""
import html
import re
import time

import requests

from .flashscore import UA

CHANNEL = "UCdb4dJKAKAxWja13JZQAx0w"
CHANNEL_URL = "https://www.youtube.com/@trifillakia_gr"
FEED = "https://www.youtube.com/feeds/videos.xml?playlist_id=UULV" + CHANNEL[2:]

_s = requests.Session()
_s.headers.update({"User-Agent": UA, "Accept-Language": "el"})


def _split_title(title):
    """«🟢 LIVE ROI MAT SHOW | Θέμα» → («ROI MAT SHOW», «Θέμα»)."""
    show, _, topic = title.partition("|")
    show = re.sub(r"[^\w\s&'.-]", " ", show)  # emoji
    show = re.sub(r"\bLIVE\b", " ", show, flags=re.I)
    show = " ".join(show.split()).strip(" -–")
    # «Θέμα| Ανοικτές Γραμμές» → «Θέμα – Ανοικτές Γραμμές»
    topic = " – ".join(p for p in (" ".join(x.split()).strip(" -–") for x in topic.split("|")) if p)
    if not topic:  # τίτλος χωρίς «|»
        return "", show
    return show, topic


def _thumb(vid):
    """Η μεγαλύτερη μικρογραφία που υπάρχει (η maxres λείπει αν δεν ανέβηκε δική μας εικόνα)."""
    for name in ("maxresdefault", "sddefault"):
        url = f"https://i.ytimg.com/vi/{vid}/{name}.jpg"
        try:
            if _s.head(url, timeout=15).status_code == 200:
                return url
        except requests.RequestException:
            pass
    return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"


def video(vid):
    """Στοιχεία μιας εκπομπής: τίτλος, ώρα έναρξης, αν είναι ακόμα προγραμματισμένη, φωτογραφία."""
    r = _s.get(f"https://www.youtube.com/watch?v={vid}", timeout=30)
    if r.status_code != 200:
        return None
    page = r.text
    m = re.search(r'"scheduledStartTime":"(\d+)"', page)
    t = re.search(r'<meta name="title" content="([^"]*)"', page) or re.search(r"<title>(.*?) - YouTube</title>", page)
    title = html.unescape(t.group(1)).strip() if t else ""
    show, topic = _split_title(title)
    return {
        "id": vid,
        "url": f"https://www.youtube.com/watch?v={vid}",
        "title": title,
        "show": show,
        "topic": topic,
        "start": int(m.group(1)) if m else None,
        "upcoming": '"isUpcoming":true' in page,
        "live": '"isLiveNow":true' in page,
        "image": _thumb(vid),
    }


LAST = {"live": [], "unknown": []}  # από το τελευταίο upcoming(): εκπομπές LIVE τώρα / σελίδες χωρίς στοιχεία


def upcoming(max_age_days=14):
    """Οι εκπομπές που είναι ακόμα προγραμματισμένες (δεν έχουν ξεκινήσει), με τη σειρά έναρξης.
    Στο ίδιο πέρασμα γεμίζει το LAST: όσες είναι LIVE τώρα και όσες η σελίδα δεν έδωσε στοιχεία
    (consent/bot check στους servers του GitHub), για το «LIVE ΤΩΡΑ / Επόμενη εκπομπή» του site."""
    LAST["live"], LAST["unknown"] = [], []
    r = _s.get(FEED, params={"nc": int(time.time())}, timeout=30)
    if r.status_code != 200:
        return []
    out = []
    for e in re.findall(r"<entry>(.*?)</entry>", r.text, re.S):
        vid = re.search(r"<yt:videoId>(.*?)</yt:videoId>", e)
        pub = re.search(r"<published>(\d{4})-(\d\d)-(\d\d)", e)
        if not vid or not pub:
            continue
        if time.time() - time.mktime(time.strptime("-".join(pub.groups()), "%Y-%m-%d")) > max_age_days * 86400:
            continue
        v = video(vid.group(1))
        if v and v["live"]:
            LAST["live"].append(v)
        elif v is None or not v["title"]:
            LAST["unknown"].append(vid.group(1))
        if v and v["upcoming"] and v["start"] and v["start"] > time.time() - 600:
            out.append(v)
    return sorted(out, key=lambda v: v["start"])
