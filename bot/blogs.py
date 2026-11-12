"""Blogs αρθρογράφων → «Αρθρογραφία» του trifillakia.gr (importer «Blogs αρθρογράφων» του Drupal Feeds).

Ίδια λογική με το syndicate.py: φτιάχνουμε docs/blogs-feed.xml στο GitHub Pages και το Feeds του Drupal
δημιουργεί blog (όχι άρθρο) με συγγραφέα τον αρθρογράφο. Η ροή κρατά όλα τα κείμενα (έως 60), οπότε την
πρώτη φορά μπαίνουν και τα παλιά. Το Drupal δεν ξαναβάζει ό,τι έχει ήδη (μοναδικό guid).

Για νέο αρθρογράφο: προσθήκη στο BLOGGERS + νέος importer στο Drupal (κλώνος του «sofia_blogs») με
συγγραφέα τον χρήστη του + εξώφυλλο blog_<username>.jpg στο βοηθητικό node 24914.
"""
import html
import os
import re
from datetime import datetime, timezone

from .cards import ROOT
from .syndicate import _item, _media_url, _og_image, _s

FEED = os.path.join(ROOT, "docs", "blogs-feed.xml")
IMG_DIR = os.path.join(ROOT, "docs", "img-blogs")
PAGES = "https://matthaios13.github.io/trifillakia-autopost/"

BLOGGERS = [
    # (κλειδί, βάση REST, φίλτρα, κατηγορία στο trifillakia)
    ("sofia", "https://panathinaikanea.gr/wp-json/wp/v2/posts", "author=4&categories=26", "Ποδοσφαιρο"),
]


def _jpg(url, guid):
    """Το Drupal θέλει JPG: ό,τι άλλο (PNG/WebP) γίνεται JPG στο docs/img-blogs (δικός του φάκελος, ώστε
    να μην τον καθαρίζει το syndicate.py)."""
    if not url or os.path.splitext(url.split("?")[0])[1].lower() in (".jpg", ".jpeg"):
        return url
    import io

    from PIL import Image

    name = re.sub(r"[^a-z0-9]+", "-", guid.lower()).strip("-") + ".jpg"
    path = os.path.join(IMG_DIR, name)
    if not os.path.exists(path):
        try:
            im = Image.open(io.BytesIO(_s.get(url, timeout=40).content))
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
    return PAGES + "img-blogs/" + name


def fetch(blogger, log=print):
    key, base, filters, category = blogger
    r = _s.get(f"{base}?{filters}&per_page=60&_fields=id,date_gmt,title,link,content,featured_media", timeout=40)
    if r.status_code != 200:
        log(f"Blogs: {key} απάντησε {r.status_code}")
        return None
    out = []
    for p in r.json():
        guid = f"blog-{key}:{p['id']}"
        image = _media_url(base, p.get("featured_media")) or _og_image(p["link"])
        out.append({
            "guid": guid,
            "source": key,
            "category": category,
            "title": html.unescape(re.sub(r"<[^>]+>", "", p["title"]["rendered"])).strip(),
            "link": p["link"],
            "body": p["content"]["rendered"],
            "image": _jpg(image, guid),
            "ts": datetime.fromisoformat(p["date_gmt"]).replace(tzinfo=timezone.utc).timestamp(),
        })
    return out


def update(log=print):
    items = []
    for b in BLOGGERS:
        got = fetch(b, log)
        if got is None:
            log("Blogs: η ροή μένει ως έχει")
            return False
        items += got
    keep = {os.path.basename(i["image"]) for i in items if i["image"].startswith(PAGES)}
    if os.path.isdir(IMG_DIR):
        for f in os.listdir(IMG_DIR):
            if f not in keep:
                os.remove(os.path.join(IMG_DIR, f))
    xml = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<rss version="2.0"><channel>'
        "<title>Trifillakia – Blogs αρθρογράφων</title>"
        "<link>https://www.trifillakia.gr</link>"
        "<description>Αυτόματη ροή blogs για το Feeds του trifillakia.gr</description>"
        + "".join(_item(i) for i in sorted(items, key=lambda i: -i["ts"]))
        + "</channel></rss>\n"
    )
    try:
        with open(FEED, encoding="utf-8") as fh:
            if fh.read() == xml:
                return False
    except OSError:
        pass
    os.makedirs(os.path.dirname(FEED), exist_ok=True)
    with open(FEED, "w", encoding="utf-8") as fh:
        fh.write(xml)
    log(f"Blogs: ροή με {len(items)} κείμενα")
    return True
