"""Ρετρό γραφικά για το «Σαν σήμερα» του trifillakia (19/11).

- cover():  εξώφυλλο άρθρου 1280×720 (καρτ ποστάλ αριστερά, «ΣΑΝ ΣΗΜΕΡΑ» + ρολόι + χρονολόγιο δεξιά)
- post():   κάρτα Instagram 1080×1350
- story():  story Instagram 1080×1920

Κάθε γεγονός του άρθρου = μικρή καρτ ποστάλ σε σέπια με τη φωτογραφία του βίντεο. Αν δεν υπάρχει βίντεο,
η κάρτα δείχνει τα σήματα των δύο ομάδων και το σκορ (ΠΑΟ από docs/crests, αντίπαλος από τις βαθμολογίες,
αλλιώς κονκάρδα με τα αρχικά). Φόντο: σκούρο πράσινο με κόκκο, βινιέτα και αχνά τριφύλλια.
"""
import io
import json
import math
import os
import random
import re
import unicodedata

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from .cards import ROOT

FONTS = os.path.join(ROOT, "assets", "fonts")
GREEN_D = (6, 38, 22)
GREEN = (0, 88, 51)
LIME = (139, 212, 72)
CREAM = (238, 226, 196)
INK = (70, 52, 30)
PAPER = (240, 232, 214)
SEPIA_D = (52, 38, 22)
SEPIA_L = (236, 220, 184)
MONTHS = ["ΙΑΝΟΥΑΡΙΟΥ", "ΦΕΒΡΟΥΑΡΙΟΥ", "ΜΑΡΤΙΟΥ", "ΑΠΡΙΛΙΟΥ", "ΜΑΙΟΥ", "ΙΟΥΝΙΟΥ", "ΙΟΥΛΙΟΥ",
          "ΑΥΓΟΥΣΤΟΥ", "ΣΕΠΤΕΜΒΡΙΟΥ", "ΟΚΤΩΒΡΙΟΥ", "ΝΟΕΜΒΡΙΟΥ", "ΔΕΚΕΜΒΡΙΟΥ"]

# Ελληνικά ονόματα ομάδων EuroLeague → όνομα στις βαθμολογίες (docs/standings.json)
EL_NAMES = {
    "μπασκον": "Baskonia", "ρεαλ": "Real Madrid", "μπαρτσ": "FC Barcelona", "φενερ": "Fenerbahce",
    "εφες": "Anadolu Efes", "αναντο": "Anadolu Efes", "μακαμπ": "Maccabi", "ζαλγκι": "Zalgiris",
    "ερυθρο": "Crvena Zvezda", "τσερβε": "Crvena Zvezda", "παρτιζ": "Partizan", "μονακ": "Monaco",
    "βαλενθ": "Valencia", "μπαγερ": "Bayern Munich", "βιρτου": "Virtus Bologna", "αρμαν": "Milan",
    "ολιμπι": "Milan", "αλμπα": "ALBA Berlin", "βιλερμ": "LDLC ASVEL", "ασβελ": "LDLC ASVEL",
    "παρι": "Paris", "ντουμπ": "Dubai", "χαποελ": "Hapoel TLV", "μπεσικ": "Besiktas",
}
PAO_RE = re.compile(r"παναθηναικ|^παο\b")

_s = requests.Session()
_s.headers.update({"User-Agent": "Mozilla/5.0 (trifillakia-bot)"})
_logo_cache = {}


def _font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


def _plain(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn").replace("ς", "σ").strip()


# ---------------------------------------------------------------- σήματα ομάδων

def _get_img(url):
    if url in _logo_cache:
        return _logo_cache[url]
    im = None
    try:
        if url.startswith("http"):
            r = _s.get(url, timeout=20)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGBA")
        elif os.path.exists(url):
            im = Image.open(url).convert("RGBA")
    except Exception:  # noqa: BLE001
        im = None
    _logo_cache[url] = im
    return im


def _standings():
    try:
        with open(os.path.join(ROOT, "docs", "standings.json"), encoding="utf-8") as fh:
            return json.load(fh).get("comps", {})
    except (OSError, ValueError):
        return {}


def logo_for(name, sport):
    """Το σήμα μιας ομάδας (RGBA) ή None."""
    p = _plain(name)
    if PAO_RE.search(p):
        f = "crest_pao_bc.png" if sport == "b" else "crest_pao_fc.png"
        return _get_img(os.path.join(ROOT, "docs", "crests", f))
    comps = _standings()
    keys = ("gbl", "euroleague") if sport == "b" else ("superleague", "cup")
    en = next((v for k, v in EL_NAMES.items() if p.startswith(k)), None) if sport == "b" else None
    for k in keys:
        for r in (comps.get(k) or {}).get("rows", []):
            t, logo = r.get("team", ""), r.get("logo", "")
            if not logo or logo.startswith("data:"):
                continue
            if (en and t == en) or (len(p) >= 3 and _plain(t)[:6] == p[:6]):
                return _get_img(logo)
    return None


def _initials_badge(name, size):
    b = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(b)
    d.ellipse([2, 2, size - 2, size - 2], fill=(214, 196, 158, 255), outline=INK + (255,), width=max(3, size // 30))
    d.ellipse([size * 0.1, size * 0.1, size * 0.9, size * 0.9], outline=INK + (140,), width=2)
    words = [w for w in re.findall(r"[^\W\d_]+", name) if len(w) > 1] or [name]
    ini = "".join(w[0] for w in words[:2]).upper()
    d.text((size / 2, size / 2), ini, font=_font("GFSDidot-Regular.ttf", int(size * 0.42)), fill=INK, anchor="mm")
    return b


def _retro(im):
    """Λίγο ξεθωριασμένο, σαν παλιό τύπωμα."""
    a = im.getchannel("A")
    rgb = im.convert("RGB")
    sep = ImageOps.colorize(ImageOps.grayscale(rgb), SEPIA_D, SEPIA_L)
    out = Image.blend(rgb, sep, 0.35)
    out.putalpha(a)
    return out


def _teams_tile(ev, w, h):
    """Χαρτί με τα δύο σήματα και το σκορ (για γεγονότα χωρίς φωτογραφία)."""
    tile = Image.new("RGB", (w, h), (226, 210, 174))
    noise = Image.effect_noise((w, h), 30).convert("L")
    tile = Image.blend(tile, Image.merge("RGB", [noise] * 3), 0.06).convert("RGBA")
    d = ImageDraw.Draw(tile)
    label = ev.get("full") or ev.get("label", "")
    m = re.match(r"(.+?)\s+[–-]\s+(.+?)\s+(\d+\s*-\s*\d+)\s*$", label)
    if not m:
        d.text((w / 2, h / 2), str(ev["year"]), font=_font("GFSDidot-Regular.ttf", int(h * 0.5)), fill=INK, anchor="mm")
        return tile
    home, away, score = m.group(1), m.group(2), m.group(3).replace(" ", "")
    s = int(min(h * 0.6, w * 0.3))
    for name, cx in ((home, w * 0.19), (away, w * 0.81)):
        lg = logo_for(name, ev.get("sport", "f"))
        lg = _retro(ImageOps.contain(lg, (s, s), Image.LANCZOS)) if lg is not None else _initials_badge(name, s)
        tile.alpha_composite(lg, (int(cx - lg.width / 2), int(h / 2 - lg.height / 2)))
    d.text((w / 2, h / 2), score, font=_font("GFSDidot-Regular.ttf", int(h * 0.22)), fill=INK, anchor="mm")
    return tile


# ---------------------------------------------------------------- στοιχεία

def _shamrock(d, cx, cy, r, fill):
    for a in (-90, 30, 150):
        x, y = cx + r * 0.62 * math.cos(math.radians(a)), cy + r * 0.62 * math.sin(math.radians(a))
        d.ellipse([x - r * 0.58, y - r * 0.58, x + r * 0.58, y + r * 0.58], fill=fill)
    d.line([cx, cy, cx + r * 0.35, cy + r * 1.5], fill=fill, width=max(2, int(r * 0.18)))


def _background(W, H, clover_x0=0):
    bg = Image.new("RGB", (W, H), GREEN_D)
    g = Image.new("L", (W, H))
    gd = ImageDraw.Draw(g)
    for i in range(0, W, 2):
        gd.line([i, 0, i, H], fill=int(70 * i / W))
    bg = Image.composite(Image.new("RGB", (W, H), GREEN), bg, g.filter(ImageFilter.GaussianBlur(40)))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    rnd = random.Random(1908)
    for _ in range(int(14 * W * H / (1280 * 720))):
        _shamrock(ld, rnd.randint(clover_x0, W), rnd.randint(-20, H), rnd.randint(18, 60), (139, 212, 72, rnd.randint(10, 26)))
    bg = Image.alpha_composite(bg.convert("RGBA"), lay)
    noise = Image.effect_noise((W, H), 28).convert("L")
    bg = Image.blend(bg.convert("RGB"), Image.merge("RGB", [noise] * 3), 0.07)
    vig = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vig).ellipse([-W * 0.2, -H * 0.28, W * 1.2, H * 1.28], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(min(W, H) // 6))
    return Image.composite(bg, Image.new("RGB", (W, H), (2, 14, 8)), vig).convert("RGBA")


def _clock(d, cx, cy, r):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=CREAM, width=max(4, r // 12))
    for i in range(12):
        a = math.radians(i * 30)
        r1 = r - (r * 0.22 if i % 3 == 0 else r * 0.14)
        d.line([cx + r1 * math.sin(a), cy - r1 * math.cos(a), cx + (r - 4) * math.sin(a), cy - (r - 4) * math.cos(a)],
               fill=CREAM, width=4 if i % 3 == 0 else 2)
    d.line([cx, cy, cx + r * 0.42 * math.sin(math.radians(-60)), cy - r * 0.42 * math.cos(math.radians(-60))], fill=CREAM, width=max(5, r // 9))
    d.line([cx, cy, cx + r * 0.68 * math.sin(math.radians(-150)), cy - r * 0.68 * math.cos(math.radians(-150))], fill=LIME, width=max(4, r // 12))
    d.ellipse([cx - r * 0.11, cy - r * 0.11, cx + r * 0.11, cy + r * 0.11], fill=LIME)
    R = r + r * 0.32
    d.arc([cx - R, cy - R, cx + R, cy + R], start=200, end=330, fill=LIME, width=max(5, r // 10))
    a = math.radians(200)
    tx, ty, k = cx + R * math.cos(a), cy + R * math.sin(a), r / 62
    d.polygon([(tx - 16 * k, ty - 2 * k), (tx + 8 * k, ty - 16 * k), (tx + 6 * k, ty + 12 * k)], fill=LIME)


def _fit_text(d, text, font, maxw):
    if d.textlength(text, font=font) <= maxw:
        return text
    while text and d.textlength(text + "…", font=font) > maxw:
        text = text[:-1]
    return text.rstrip(" ·–-") + "…"


def _postcard(ev, w):
    """Μικρή καρτ ποστάλ: σέπια φωτογραφία 16:9 (ή τα σήματα των ομάδων) + λεζάντα."""
    ih, pad = int(w * 9 / 16), max(10, w // 27)
    cap = int(w * 0.15)
    card = Image.new("RGBA", (w + 2 * pad, ih + pad + cap), PAPER + (255,))
    photo = None
    if ev.get("img"):
        try:
            im = ImageOps.fit(Image.open(io.BytesIO(ev["img"])).convert("RGB"), (w, ih), Image.LANCZOS)
            gray = ImageOps.autocontrast(ImageOps.grayscale(im), cutoff=1)
            sep = ImageOps.colorize(gray, SEPIA_D, SEPIA_L, mid=(150, 120, 80))
            noise = Image.effect_noise(sep.size, 40).convert("L")
            photo = Image.blend(sep, Image.merge("RGB", [noise] * 3), 0.08).convert("RGBA")
        except Exception:  # noqa: BLE001
            photo = None
    card.alpha_composite(photo if photo is not None else _teams_tile(ev, w, ih), (pad, pad))
    d = ImageDraw.Draw(card)
    fy = _font("FiraSansExtraCondensed-Black.ttf", int(cap * 0.56))
    ft = _font("FiraSansExtraCondensed-Medium.ttf", int(cap * 0.5))
    y = pad + ih + cap // 2 + 1
    d.text((pad + 2, y), str(ev["year"]), font=fy, fill=GREEN if ev.get("main") else INK, anchor="lm")
    yw = d.textlength(str(ev["year"]), font=fy) + cap * 0.25
    d.text((pad + 2 + yw, y), _fit_text(d, ev.get("label", ""), ft, w - yw - 4), font=ft, fill=INK, anchor="lm")
    if ev.get("main"):
        tw = int(w * 0.33)
        tape = Image.new("RGBA", (tw, int(tw * 0.29)), (139, 212, 72, 210)).rotate(-8, expand=True)
        card.alpha_composite(tape, (card.width // 2 - tape.width // 2, 0))
    return card


def _collage(bg, events, box, cw, seed):
    """Μέχρι 6 καρτ ποστάλ σε πλέγμα 2 στηλών, κεντραρισμένες μέσα στο box=(x,y,w,h)."""
    evs = events[:6]
    n = len(evs)
    if not n:
        return
    cols = 1 if n == 1 else 2
    rows = math.ceil(n / cols)
    if n == 1:
        cw = int(cw * 1.8)
    bx, by, bw, bh = box
    # να χωράει: ύψος κάρτας ≈ 0.80·w (16:9 + περιθώριο + λεζάντα), πλάτος ≈ 1.08·w
    cw = int(min(cw, (bh / rows) / 0.86, (bw / cols) / 1.18))
    rnd = random.Random(seed)
    cards = [_postcard(e, cw) for e in evs]
    cwid, ch = cards[0].width, cards[0].height
    gap_x = int(cwid * 0.08)
    gap_y = min(int(ch * 0.12), max(8, (bh - rows * ch) // max(1, rows - 1))) if rows > 1 else 0
    tot_h = rows * ch + (rows - 1) * gap_y
    y0 = by + (bh - tot_h) // 2
    x0 = bx + (bw - (cols * cwid + (cols - 1) * gap_x)) // 2
    for i, c in enumerate(cards):
        r, k = divmod(i, cols)
        if n % 2 == 1 and i == n - 1 and cols == 2:
            k = 0.5
        c = c.rotate(rnd.uniform(-5, 5), resample=Image.BICUBIC, expand=True)
        sh = Image.new("RGBA", c.size, (0, 0, 0, 0))
        sh.paste((0, 0, 0, 140), mask=c.split()[3])
        sh = sh.filter(ImageFilter.GaussianBlur(10))
        x = int(x0 + k * (cwid + gap_x) + rnd.randint(-8, 8))
        y = int(y0 + r * (ch + gap_y) + rnd.randint(-6, 6))
        bg.alpha_composite(sh, (x + 8, y + 10))
        bg.alpha_composite(c, (x, y))


def _timeline(d, events, x0, x1, y0, size):
    ys = sorted({e["year"] for e in events})[:8]
    if not ys:
        return
    main = events[0]["year"]
    d.line([x0 - 10, y0, x1 + 10, y0], fill=(200, 190, 160), width=3)
    step = (x1 - x0) / (len(ys) - 1) if len(ys) > 1 else 0
    f = _font("FiraSansExtraCondensed-SemiBold.ttf", size)
    for i, yv in enumerate(ys):
        x = x0 + i * step if len(ys) > 1 else (x0 + x1) / 2
        big = yv == main
        r = size * (0.43 if big else 0.27)
        d.ellipse([x - r, y0 - r, x + r, y0 + r], fill=LIME if big else CREAM, outline=GREEN_D, width=3)
        d.text((x, y0 + (size if i % 2 == 0 else -size)), str(yv), font=f, fill=LIME if big else CREAM, anchor="mm")


def _logo(bg, maxw, pos):
    try:
        lg = Image.open(os.path.join(ROOT, "assets", "trifi_logo.png")).convert("RGBA")
        lg.thumbnail((maxw, maxw))
        x, y = pos
        bg.alpha_composite(lg, (int(x - lg.width), int(y - lg.height)))
    except OSError:
        pass


def with_images(events):
    """Κατεβάζει τη μικρογραφία YouTube κάθε γεγονότος (mqdefault = 16:9 χωρίς μαύρες μπάρες)."""
    out = []
    for i, e in enumerate(events):
        e = dict(e, main=i == 0)
        if e.get("yt") and "img" not in e:
            try:
                r = _s.get(f"https://i.ytimg.com/vi/{e['yt']}/mqdefault.jpg", timeout=20)
                e["img"] = r.content if r.status_code == 200 and len(r.content) > 2000 else None
            except requests.RequestException:
                e["img"] = None
        out.append(e)
    return out


# ---------------------------------------------------------------- διατάξεις

def cover(events, day, month, out_path):
    """Εξώφυλλο άρθρου 1280×720."""
    W, H = 1280, 720
    bg = _background(W, H, clover_x0=560)
    _collage(bg, events, (40, 0, 600, H), 270, day * 100 + month)
    d = ImageDraw.Draw(bg)
    X = 690
    d.text((X, 92), "TRIFILLAKIA.GR · ΙΣΤΟΡΙΑ", font=_font("FiraSansExtraCondensed-SemiBold.ttf", 26), fill=LIME)
    d.text((X - 4, 118), "ΣΑΝ", font=_font("FiraSansExtraCondensed-Black.ttf", 112), fill=CREAM)
    d.text((X - 4, 222), "ΣΗΜΕΡΑ", font=_font("FiraSansExtraCondensed-Black.ttf", 132), fill=CREAM)
    d.text((X, 372), f"{day} {MONTHS[month - 1]}", font=_font("GFSDidot-Regular.ttf", 52), fill=LIME)
    _clock(d, 1150, 170, 62)
    _timeline(d, events, X + 10, W - 70, 520, 30)
    _logo(bg, 170, (W - 40, H - 26))
    bg.convert("RGB").save(out_path, "JPEG", quality=88, optimize=True)
    return out_path


def _portrait(events, day, month, W, H, foot):
    bg = _background(W, H)
    d = ImageDraw.Draw(bg)
    top = 60 if H < 1600 else 150
    d.text((60, top), "TRIFILLAKIA.GR · ΙΣΤΟΡΙΑ", font=_font("FiraSansExtraCondensed-SemiBold.ttf", 34), fill=LIME)
    d.text((54, top + 34), "ΣΑΝ ΣΗΜΕΡΑ", font=_font("FiraSansExtraCondensed-Black.ttf", 150), fill=CREAM)
    d.text((60, top + 212), f"{day} {MONTHS[month - 1]}", font=_font("GFSDidot-Regular.ttf", 64), fill=LIME)
    _clock(d, W - 150, top + 140, 82)
    grid_top = top + 310
    tl_y = H - (210 if H < 1600 else 420)
    _collage(bg, events, (30, grid_top, W - 60, tl_y - grid_top - 60), 400, day * 100 + month)
    d = ImageDraw.Draw(bg)
    _timeline(d, events, 110, W - 110, tl_y, 36)
    foot(bg, d)
    return bg


def post(events, day, month, out_path=None):
    """Κάρτα Instagram 1080×1350 (επιστρέφει RGBA εικόνα)."""
    W, H = 1080, 1350

    def foot(bg, d):
        d.text((60, H - 62), "ΔΙΑΒΑΣΤΕ ΠΕΡΙΣΣΟΤΕΡΑ ΣΤΟ TRIFILLAKIA.GR", font=_font("FiraSans-SemiBold.ttf", 30), fill=(190, 230, 150), anchor="lm")
        d.text((W - 60, H - 62), "LINK ΣΤΟ BIO", font=_font("FiraSansExtraCondensed-ExtraBold.ttf", 34), fill=(255, 255, 255), anchor="rm")

    bg = _portrait(events, day, month, W, H, foot)
    if out_path:
        bg.convert("RGB").save(out_path, "JPEG", quality=90)
    return bg


def story(events, day, month, out_path=None):
    """Story Instagram 1080×1920 (επιστρέφει RGBA εικόνα)."""
    W, H = 1080, 1920

    def foot(bg, d):
        d.rounded_rectangle((60, H - 250, W - 60, H - 150), radius=50, fill=LIME)
        d.text((W / 2, H - 200), "ΤΟ ΑΡΘΡΟ ΣΤΟ LINK ΤΟΥ BIO", font=_font("FiraSansExtraCondensed-Black.ttf", 50), fill=GREEN_D, anchor="mm")
        d.text((W / 2, H - 90), "@trifillakiagr", font=_font("FiraSans-SemiBold.ttf", 38), fill=(190, 210, 190), anchor="mm")

    bg = _portrait(events, day, month, W, H, foot)
    if out_path:
        bg.convert("RGB").save(out_path, "JPEG", quality=90)
    return bg
