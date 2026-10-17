"""Η σελίδα «link στο bio» του Instagram (GitHub Pages, φάκελος docs/): τα τελευταία άρθρα σε πλέγμα."""
import html
import os
import shutil

from .cards import ASSETS, ROOT

DOCS = os.path.join(ROOT, "docs")

LINKS = [
    ("Trifillakia.gr", "https://www.trifillakia.gr"),
    ("Facebook", "https://www.facebook.com/349363601832677"),
    ("Instagram", "https://www.instagram.com/trifillakiagr/"),
]

PAGE = """<!doctype html>
<html lang="el">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Trifillakia.gr</title>
<meta name="description" content="Οι τελευταίες ειδήσεις του Trifillakia.gr">
<link rel="icon" href="logo.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fira+Sans+Extra+Condensed:wght@600;800&display=swap" rel="stylesheet">
<style>
  :root {{ --bg:#021a0b; --card:#06331a; --neon:#58e65a; --text:#fff; --muted:#bfe1c3; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--text); font-family:"Fira Sans Extra Condensed", system-ui, sans-serif; }}
  .wrap {{ max-width:720px; margin:0 auto; padding:24px 16px 48px; }}
  header {{ text-align:center; }}
  header img {{ width:220px; max-width:60%; }}
  .links {{ display:flex; flex-wrap:wrap; gap:10px; justify-content:center; margin:18px 0 24px; }}
  .links a {{ color:var(--bg); background:var(--neon); text-decoration:none; font-weight:800; padding:10px 18px; border-radius:999px; font-size:17px; }}
  h2 {{ font-weight:800; letter-spacing:.5px; margin:8px 0 12px; font-size:20px; color:var(--muted); }}
  .grid {{ display:grid; grid-template-columns:repeat(3, 1fr); gap:6px; }}
  .grid a {{ position:relative; display:block; aspect-ratio:4/5; overflow:hidden; border-radius:6px; background:var(--card); color:var(--text); text-decoration:none; }}
  .grid img {{ width:100%; height:100%; object-fit:cover; display:block; }}
  .grid span {{ position:absolute; left:0; right:0; bottom:0; padding:28px 7px 7px; font-weight:600; font-size:13px; line-height:1.15;
               background:linear-gradient(transparent, rgba(2,26,11,.95)); }}
  .grid em {{ font-style:normal; display:block; color:var(--neon); font-size:11px; font-weight:800; }}
  @media (max-width:420px) {{ .grid span {{ font-size:11.5px; }} }}
  footer {{ text-align:center; color:var(--muted); margin-top:28px; font-size:14px; }}
</style>
</head>
<body>
<div class="wrap">
  <header><img src="logo.png" alt="Trifillakia.gr"></header>
  <nav class="links">{links}</nav>
  <h2>ΤΕΛΕΥΤΑΙΑ ΝΕΑ</h2>
  <main class="grid">{items}</main>
  <footer>☘️ trifillakia.gr</footer>
</div>
</body>
</html>
"""


def thumb(url):
    """Μικρό αντίγραφο της φωτογραφίας από το Drupal (320x320), αντί για το πρωτότυπο που μπορεί να είναι τεράστιο."""
    return url.replace("/sites/default/files/field/image/", "/sites/default/files/styles/image_320x320/public/field/image/")


def write(recent):
    os.makedirs(DOCS, exist_ok=True)
    logo = os.path.join(DOCS, "logo.png")
    if not os.path.exists(logo):
        shutil.copy(os.path.join(ASSETS, "trifi_logo.png"), logo)
    nojekyll = os.path.join(DOCS, ".nojekyll")
    if not os.path.exists(nojekyll):
        open(nojekyll, "w").close()
    e = html.escape
    links = "".join(f'<a href="{e(u)}">{e(t)}</a>' for t, u in LINKS)
    items = "".join(
        f'<a href="{e(a["url"])}"><img src="{e(thumb(a["image"]))}" alt="" loading="lazy">'
        f'<span>{"<em>" + e(a["label"]) + "</em>" if a.get("label") else ""}{e(a["title"])}</span></a>'
        for a in recent[:30]
    )
    page = PAGE.format(links=links, items=items)
    path = os.path.join(DOCS, "index.html")
    try:
        with open(path, encoding="utf-8") as fh:
            if fh.read() == page:
                return
    except OSError:
        pass
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(page)
