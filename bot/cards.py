"""Οι κάρτες (Pillow): GAME DAY, FULL TIME, ΒΑΘΜΟΛΟΓΙΑ, MVP. Feed 1080x1350 και Story 1080x1920."""
import io
import math
import os
import random
import unicodedata
from datetime import datetime
from functools import lru_cache

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .config import TZ

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
LOGOS = os.path.join(ROOT, "logos")

W, H = 1080, 1350
SH = 1920

DARK = (2, 26, 11)
DEEP = (4, 48, 20)
GREEN = (9, 110, 48)
NEON = (88, 230, 90)
NEON_SOFT = (150, 245, 140)
WHITE = (255, 255, 255)
MUTED = (190, 225, 195)

DAYS = ["ΔΕΥΤΕΡΑ", "ΤΡΙΤΗ", "ΤΕΤΑΡΤΗ", "ΠΕΜΠΤΗ", "ΠΑΡΑΣΚΕΥΗ", "ΣΑΒΒΑΤΟ", "ΚΥΡΙΑΚΗ"]
MONTHS = ["ΙΑΝΟΥΑΡΙΟΥ", "ΦΕΒΡΟΥΑΡΙΟΥ", "ΜΑΡΤΙΟΥ", "ΑΠΡΙΛΙΟΥ", "ΜΑΪΟΥ", "ΙΟΥΝΙΟΥ", "ΙΟΥΛΙΟΥ", "ΑΥΓΟΥΣΤΟΥ", "ΣΕΠΤΕΜΒΡΙΟΥ", "ΟΚΤΩΒΡΙΟΥ", "ΝΟΕΜΒΡΙΟΥ", "ΔΕΚΕΜΒΡΙΟΥ"]


def font(weight, size):
    name = {
        "black": "FiraSansExtraCondensed-Black.ttf",
        "xbold": "FiraSansExtraCondensed-ExtraBold.ttf",
        "semi": "FiraSansExtraCondensed-SemiBold.ttf",
        "medium": "FiraSansExtraCondensed-Medium.ttf",
    }[weight]
    return _font(name, size)


@lru_cache(maxsize=None)
def _font(name, size):
    return ImageFont.truetype(os.path.join(ASSETS, "fonts", name), size)


def upper(s):
    """Κεφαλαία χωρίς τόνους (τα διαλυτικά μένουν: ΠΑΝΑΘΗΝΑΪΚΟΣ)."""
    s = unicodedata.normalize("NFD", s.upper())
    s = "".join(c for c in s if c not in ("́", "΄"))
    return unicodedata.normalize("NFC", s)


# --------------------------------------------------------------------------
# Εικόνες
# --------------------------------------------------------------------------

_img_cache = {}


def fetch_image(url):
    if not url:
        return None
    if url in _img_cache:
        return _img_cache[url]
    im = None
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            im = Image.open(io.BytesIO(r.content)).convert("RGBA")
    except Exception:
        im = None
    _img_cache[url] = im
    return im


def crest_image(team_id, url, pao_file=None):
    """Σήμα: πρώτα logos/<flashscore id>.png, μετά το σήμα του ΠΑΟ, μετά το Flashscore (μεγεθυμένο)."""
    for path in (os.path.join(LOGOS, f"{team_id}.png") if team_id else None, os.path.join(LOGOS, pao_file) if pao_file else None):
        if path and os.path.exists(path):
            return Image.open(path).convert("RGBA")
    return fetch_image(url)


def fit(im, box):
    if im is None:
        return None
    im = im.copy()
    bb = im.getchannel("A").getbbox()
    if bb:
        im = im.crop(bb)
    scale = min(box / im.width, box / im.height)
    out = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    if scale > 1.5:
        out = out.filter(ImageFilter.UnsharpMask(radius=2, percent=80, threshold=2))
    return out


def paste_center(canvas, im, cx, cy, shadow=True):
    if im is None:
        return
    x, y = int(cx - im.width / 2), int(cy - im.height / 2)
    if shadow:
        pad = 60
        a = Image.new("L", (im.width + pad * 2, im.height + pad * 2), 0)
        a.paste(im.getchannel("A"), (pad, pad))
        a = a.filter(ImageFilter.GaussianBlur(18)).point(lambda v: int(v * 0.6))
        glow = Image.new("RGBA", a.size, (0, 0, 0, 0))
        glow.putalpha(a)
        canvas.alpha_composite(glow, (x - pad + 6, y - pad + 14))
    canvas.alpha_composite(im, (x, y))


@lru_cache(maxsize=None)
def logo():
    return Image.open(os.path.join(ASSETS, "trifi_logo.png")).convert("RGBA")


# --------------------------------------------------------------------------
# Φόντο
# --------------------------------------------------------------------------


@lru_cache(maxsize=4)
def _background(h, seed):
    rnd = random.Random(seed)
    img = Image.new("RGBA", (W, h), DARK + (255,))

    # φωτεινό κέντρο (απαλό)
    glow = Image.new("L", (W, h), 0)
    ImageDraw.Draw(glow).ellipse((-W * 0.25, h * 0.08, W * 1.25, h * 0.82), fill=255)
    glow = glow.filter(ImageFilter.GaussianBlur(220))
    img.paste(Image.new("RGBA", (W, h), GREEN + (255,)), (0, 0), glow)
    dark = Image.new("L", (W, h), 0)
    ImageDraw.Draw(dark).rectangle((0, h * 0.8, W, h), fill=150)
    dark = dark.filter(ImageFilter.GaussianBlur(160))
    img.paste(Image.new("RGBA", (W, h), DARK + (255,)), (0, 0), dark)

    # λεπτές διαγώνιες ρίγες (υφή)
    stripes = Image.new("RGBA", (W, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stripes)
    for x in range(-h, W, 26):
        sd.line([(x, h), (x + h, 0)], fill=(255, 255, 255, 7), width=8)
    img.alpha_composite(stripes)

    # δέσμες neon γραμμών στις γωνίες (πάνω αριστερά, κάτω δεξιά)
    streaks = Image.new("RGBA", (W, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(streaks)
    for (ox, oy, sx, sy) in ((0, 0, 1, 1), (W, h, -1, -1)):
        for i in range(6):
            t = 120 + i * 46 + rnd.randint(-10, 10)
            width = rnd.choice([3, 5, 8, 12])
            alpha = rnd.randint(120, 230)
            d.line([(ox + sx * t, oy), (ox, oy + sy * t * 1.35)], fill=NEON + (alpha,), width=width)
    blur = streaks.filter(ImageFilter.GaussianBlur(16))
    img.alpha_composite(blur)
    img.alpha_composite(blur)
    img.alpha_composite(streaks)

    # μεγάλο αχνό τριφύλλι
    wm = fit(Image.open(os.path.join(LOGOS, "pao_ao.png")).convert("RGBA"), int(W * 1.1))
    white = Image.new("RGBA", wm.size, WHITE + (0,))
    white.putalpha(wm.getchannel("A").point(lambda v: int(v * 0.05)))
    img.alpha_composite(white, (int((W - wm.width) / 2), int(h * 0.45 - wm.height / 2)))

    # θόρυβος
    noise = Image.effect_noise((W, h), 40).convert("L")
    nl = Image.merge("RGBA", (noise, noise, noise, Image.new("L", (W, h), 10)))
    img.alpha_composite(nl)
    return img


def background(h=H, seed=7):
    return _background(h, seed).copy()


# --------------------------------------------------------------------------
# Βοηθητικά σχεδίασης
# --------------------------------------------------------------------------


def shape(canvas, kind, *args, **kw):
    """Ημιδιάφανο σχήμα πάνω στον καμβά (το ImageDraw σε RGBA αντικαθιστά, δεν αναμειγνύει)."""
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    getattr(ImageDraw.Draw(layer), kind)(*args, **kw)
    canvas.alpha_composite(layer)


def text_w(d, s, f):
    b = d.textbbox((0, 0), s, font=f)
    return b[2] - b[0]


def shrink(d, s, weight, size, maxw, minsize=24):
    while size > minsize and text_w(d, s, font(weight, size)) > maxw:
        size -= 2
    return font(weight, size)


def ctext(d, cx, y, s, f, fill=WHITE, anchor="mt"):
    d.text((cx, y), s, font=f, fill=fill, anchor=anchor)


def glow_text(canvas, xy, s, f, fill=WHITE, glow=NEON, radius=16, strength=2, anchor="mt", outline=False):
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text(xy, s, font=f, fill=glow + (255,), anchor=anchor)
    g = layer.filter(ImageFilter.GaussianBlur(radius))
    for _ in range(strength):
        canvas.alpha_composite(g)
    d = ImageDraw.Draw(canvas, "RGBA")
    if outline:
        d.text(xy, s, font=f, fill=(0, 0, 0, 0), anchor=anchor, stroke_width=4, stroke_fill=fill)
    else:
        d.text(xy, s, font=f, fill=fill, anchor=anchor)


def pill(canvas, cx, y, s, f, bg=NEON, fg=DARK, padx=34, pady=14):
    d = ImageDraw.Draw(canvas, "RGBA")
    w = text_w(d, s, f)
    b = d.textbbox((0, 0), s, font=f)
    h = b[3] - b[1]
    box = (cx - w / 2 - padx, y, cx + w / 2 + padx, y + h + pady * 2)
    d.rounded_rectangle(box, radius=(h + pady * 2) / 2, fill=bg)
    d.text((cx, y + pady - b[1]), s, font=f, fill=fg, anchor="mt")
    return box[3]


def comp_logo(m):
    """Logo διοργάνωσης: logos/comp/<flashscore tour_id>.png (επίσημα logos), αλλιώς του Flashscore."""
    local = os.path.join(LOGOS, "comp", f"{m.get('tour_id') or '-'}.png")
    if os.path.exists(local):
        return Image.open(local).convert("RGBA")
    return fetch_image(m.get("comp_logo"))


def badge_image(m, size, maxw=None):
    """Το logo σε «σήμα» ύψους size: τα logo-πλακίδια μένουν όπως είναι, τα σκούρα σε λευκό, τα ανοιχτά σε σκούρο."""
    im = comp_logo(m)
    if im is None:
        return None
    bb = im.getchannel("A").getbbox()
    if bb:
        im = im.crop(bb)
    maxw = maxw or int(size * 2.8)
    a = im.getchannel("A")
    corners = [a.getpixel(p) for p in ((0, 0), (im.width - 1, 0), (0, im.height - 1), (im.width - 1, im.height - 1))]
    if min(corners) > 200:  # πλακίδιο
        scale = min(size / im.height, maxw / im.width)
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
        mask = Image.new("L", im.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius=int(min(im.size) * 0.14), fill=255)
        out = Image.new("RGBA", (im.width + 8, im.height + 8), (0, 0, 0, 0))
        ImageDraw.Draw(out).rounded_rectangle((0, 0, out.width - 1, out.height - 1), radius=int(min(im.size) * 0.14) + 4, fill=NEON + (255,))
        out.paste(im, (4, 4), mask)
        return out
    # φωτεινότητα του logo
    small = im.copy()
    small.thumbnail((120, 120))
    px = [(r, g, b) for (r, g, b, al) in small.getdata() if al > 128]
    lum = sum(0.299 * r + 0.587 * g + 0.114 * b for r, g, b in px) / max(1, len(px)) / 255
    bg = DARK if lum > 0.62 else WHITE
    inner = int(size * 0.74)
    scale = min(inner / im.height, (maxw - size * 0.36) / im.width)
    if scale > 1.5:
        lg = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 80, 2))
    else:
        lg = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    w = max(size, lg.width + int(size * 0.36))
    out = Image.new("RGBA", (w + 6, size + 6), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    d.rounded_rectangle((0, 0, w + 5, size + 5), radius=(size + 6) // 2, fill=NEON + (255,))
    d.rounded_rectangle((3, 3, w + 2, size + 2), radius=size // 2, fill=bg + (255,))
    out.alpha_composite(lg, ((out.width - lg.width) // 2, (out.height - lg.height) // 2))
    return out


def comp_badge(canvas, m, cx, cy, size, maxw=None):
    im = badge_image(m, size, maxw)
    if im is None:
        return 0
    paste_center(canvas, im, cx, cy, shadow=True)
    return im.width


def header(canvas, label):
    """Logo Trifillakia πάνω και η ετικέτα του τμήματος."""
    lg = fit(logo(), 300)
    canvas.alpha_composite(lg, (int((W - lg.width) / 2), 52))
    return pill(canvas, W / 2, 52 + lg.height + 22, label, font("xbold", 34))


def footer(canvas, h, text="@trifillakiagr"):
    d = ImageDraw.Draw(canvas, "RGBA")
    y = h - 70
    d.line([(90, y), (W / 2 - 150, y)], fill=NEON + (255,), width=3)
    d.line([(W / 2 + 150, y), (W - 90, y)], fill=NEON + (255,), width=3)
    ctext(d, W / 2, y, text, font("semi", 34), fill=MUTED, anchor="mm")


def team_block(canvas, cx, cy, crest, name, size=250):
    paste_center(canvas, fit(crest, size), cx, cy)
    d = ImageDraw.Draw(canvas, "RGBA")
    s = upper(name)
    f = shrink(d, s, "xbold", 44, 380)
    ctext(d, cx, cy + size / 2 + 26, s, f)


def date_line(ts):
    dt = datetime.fromtimestamp(ts, TZ)
    return f"{DAYS[dt.weekday()]} {dt.day} {MONTHS[dt.month - 1]}", dt.strftime("%H:%M")


# --------------------------------------------------------------------------
# Κάρτες
# --------------------------------------------------------------------------


def gameday(m):
    """m: label, comp, round, start, home, away, home_crest, away_crest, venue."""
    c = background(seed=11)
    y = header(c, m["label"])
    glow_text(c, (W / 2, y + 20), "GAME DAY", font("black", 210), radius=22)

    cy = y + 410
    team_block(c, W * 0.25, cy, m["home_crest"], m["home"])
    team_block(c, W * 0.75, cy, m["away_crest"], m["away"])
    glow_text(c, (W / 2, cy - 40), "VS", font("black", 110), fill=NEON_SOFT, anchor="mm", radius=12, strength=1)
    comp_badge(c, m, W / 2, cy + 80, 110, 230)

    d = ImageDraw.Draw(c, "RGBA")
    day, hour = date_line(m["start"])
    by = cy + 225
    shape(c, "line", [(160, by), (W - 160, by)], fill=NEON + (160,), width=2)
    comp = upper(m["comp"] + (f" | {m['round']}" if m.get("round") else ""))
    ctext(d, W / 2, by + 26, comp, shrink(d, comp, "xbold", 46, W - 160), fill=NEON_SOFT)
    ctext(d, W / 2, by + 90, day, font("semi", 44), fill=WHITE)
    glow_text(c, (W / 2, by + 146), hour, font("black", 120), radius=14, strength=1)
    if m.get("venue"):
        v = upper(m["venue"])
        ctext(d, W / 2, by + 282, v, shrink(d, v, "medium", 38, W - 200), fill=MUTED)
    footer(c, H)
    return c


def fulltime(m):
    """m: label, comp, round, home, away, crests, home_score, away_score, periods, goals, sport, info."""
    c = background(seed=23)
    y = header(c, m["label"])
    glow_text(c, (W / 2, y + 20), "FULL TIME", font("black", 200), radius=22)

    cy = y + 400
    team_block(c, W * 0.2, cy, m["home_crest"], m["home"], size=230)
    team_block(c, W * 0.8, cy, m["away_crest"], m["away"], size=230)
    score = f"{m['home_score']}-{m['away_score']}"
    comp_badge(c, m, W / 2, cy + 120, 100, 300)
    glow_text(c, (W / 2, cy - 40), score, shrink(ImageDraw.Draw(c, "RGBA"), score, "black", 190, 440), anchor="mm", radius=18)

    d = ImageDraw.Draw(c, "RGBA")
    by = cy + 205
    shape(c, "line", [(140, by), (W - 140, by)], fill=NEON + (160,), width=2)
    comp = upper(m["comp"] + (f" | {m['round']}" if m.get("round") else ""))
    ctext(d, W / 2, by + 24, comp, shrink(d, comp, "xbold", 42, W - 160), fill=NEON_SOFT)
    by += 100

    if m["sport"] == "football" and m.get("goals"):
        f = font("xbold", 36)
        rows = {"home": [], "away": []}
        for g in m["goals"]:
            note = f" ({g['note']})" if g["note"] else ""
            rows[g["side"]].append(f"{g['player']} {g['minute']}{note}")
        n = max(len(rows["home"]), len(rows["away"]))
        if n > 4:
            f = font("semi", 28)
        step = 44 if n <= 4 else 36
        for i in range(min(n, 6)):
            for side, x in (("home", W * 0.25), ("away", W * 0.75)):
                if i < len(rows[side]):
                    ctext(d, x, by + i * step, rows[side][i], f, fill=WHITE)
        by += min(n, 6) * step + 10
    elif m.get("periods"):
        per = m["periods"]
        names = {"basketball": "Δ", "volleyball": "Σ", "water-polo": "Π"}.get(m["sport"], "Π")
        cell = min(170, (W - 200) // len(per))
        x0 = W / 2 - cell * len(per) / 2
        for i, (h, a) in enumerate(per):
            cx = x0 + cell * i + cell / 2
            lbl = f"{i + 1}{names}" if i < 4 or m["sport"] == "volleyball" else "ΠΑΡ"
            ctext(d, cx, by, lbl, font("semi", 28), fill=NEON_SOFT)
            ctext(d, cx, by + 38, f"{h}-{a}", font("xbold", 44), fill=WHITE)
        by += 110

    if m.get("venue"):
        v = upper(m["venue"])
        ctext(d, W / 2, max(by + 20, H - 170), v, shrink(d, v, "medium", 34, W - 200), fill=MUTED)
    footer(c, H)
    return c


def standings(m):
    """m: label, comp, round, rows, pao_id, sport."""
    c = background(seed=37)
    y = header(c, m["label"])
    glow_text(c, (W / 2, y + 16), "ΒΑΘΜΟΛΟΓΙΑ", font("black", 130), radius=18)
    d = ImageDraw.Draw(c, "RGBA")
    sub = upper(m["comp"] + (f" | {m['round']}" if m.get("round") else ""))
    bimg = badge_image(m, 70, 220)
    bw = bimg.width + 20 if bimg else 0
    sf = shrink(d, sub, "xbold", 40, W - 160 - bw)
    tw = text_w(d, sub, sf)
    x0 = W / 2 - (tw + bw) / 2
    if bimg:
        paste_center(c, bimg, x0 + bimg.width / 2, y + 182, shadow=False)
        x0 += bw
    d.text((x0, y + 160), sub, font=sf, fill=NEON_SOFT, anchor="lt")

    rows = m["rows"]
    top = y + 225
    avail = H - 110 - top
    maxrows = 20
    if len(rows) > maxrows:
        idx = next((i for i, r in enumerate(rows) if r["id"] == m["pao_id"]), 0)
        start = max(0, min(idx - maxrows // 2, len(rows) - maxrows))
        rows = rows[start : start + maxrows]
    rh = min(58, (avail - 50) // max(1, len(rows)))
    draws = m["sport"] in ("football", "water-polo") and any(r["d"] for r in m["rows"]) or m["sport"] == "football"
    cols = [("ΑΓ", "played")] + [("Ν", "w")] + ([("Ι", "d")] if draws else []) + [("Η", "l")]
    diff_lbl = {"football": "ΓΚΟΛ", "basketball": "ΠΟΝΤΟΙ", "volleyball": "ΣΕΤ", "water-polo": "ΓΚΟΛ"}.get(m["sport"], "+/-")
    fsz = max(22, int(rh * 0.5))
    fr = font("semi", fsz)
    fb = font("xbold", fsz)
    x_rank, x_logo, x_name = 90, 150, 196
    x_cols = W - 90 - 80 * (len(cols) + 2)
    hy = top
    ctext(d, x_rank, hy, "#", font("semi", 26), fill=MUTED)
    for i, (lbl, _) in enumerate(cols):
        ctext(d, x_cols + 80 * i + 40, hy, lbl, font("semi", 26), fill=MUTED)
    ctext(d, x_cols + 80 * len(cols) + 60, hy, diff_lbl, font("semi", 26), fill=MUTED)
    ctext(d, W - 110, hy, "ΒΑΘ", font("semi", 26), fill=MUTED)
    ry = top + 44
    for r in rows:
        ours = r["id"] == m["pao_id"]
        if ours:
            shape(c, "rounded_rectangle", (60, ry - 4, W - 60, ry + rh - 4), radius=12, fill=NEON + (235,))
        elif r["rank"] % 2 == 0:
            shape(c, "rectangle", (60, ry - 4, W - 60, ry + rh - 4), fill=(255, 255, 255, 16))
        col = DARK if ours else WHITE
        cy = ry + rh / 2 - 4
        ctext(d, x_rank, cy, str(r["rank"]), fb, fill=col, anchor="mm")
        lg = fit(fetch_image(r["logo"]), int(rh * 0.7))
        if lg:
            c.alpha_composite(lg, (int(x_logo - lg.width / 2), int(cy - lg.height / 2)))
        name = upper(r["name"])
        d.text((x_name, cy), name, font=shrink(d, name, "xbold" if ours else "semi", fsz, x_cols - x_name - 20, 18), fill=col, anchor="lm")
        for i, (_, k) in enumerate(cols):
            ctext(d, x_cols + 80 * i + 40, cy, str(r[k]), fr, fill=col, anchor="mm")
        ctext(d, x_cols + 80 * len(cols) + 60, cy, f"{r['gf']}:{r['ga']}", font("semi", max(18, fsz - 4)), fill=col, anchor="mm")
        ctext(d, W - 110, cy, str(r["pts"]), fb, fill=col, anchor="mm")
        ry += rh
    footer(c, H)
    return c


def mvp(m):
    """m: label, comp, first, last, photo, stats [(value, label)], home, away, score, pao_crest."""
    c = background(seed=53)
    d = ImageDraw.Draw(c, "RGBA")
    lg = fit(logo(), 230)
    c.alpha_composite(lg, (W - lg.width - 50, 46))
    crest = fit(m.get("pao_crest"), 150)
    if crest:
        c.alpha_composite(crest, (60, 40))
    bimg = badge_image(m, 110, 330)
    if bimg:
        paste_center(c, bimg, 240 + bimg.width / 2, 115, shadow=False)

    photo = fetch_image(m.get("photo"))
    if photo:
        ph = fit(photo, 1080)
        ph_h = int(H * 0.86)
        scale = ph_h / ph.height
        ph = ph.resize((int(ph.width * scale), ph_h), Image.LANCZOS)
        px = int(W - ph.width * 0.86)
        # σβήσιμο στις άκρες, για φωτογραφίες με δικό τους φόντο
        fade = Image.new("L", ph.size, 255)
        fd = ImageDraw.Draw(fade)
        edge = int(ph.width * 0.3)
        for i in range(edge):
            fd.line([(i, 0), (i, ph.height)], fill=int(255 * (i / edge) ** 1.4))
        top = int(ph.height * 0.08)
        for i in range(top):
            fd.line([(0, i), (ph.width, i)], fill=int(255 * i / top))
        from PIL import ImageChops
        ph.putalpha(ImageChops.multiply(ph.getchannel("A"), fade))
        glow = ph.getchannel("A").filter(ImageFilter.GaussianBlur(30))
        gl = Image.new("RGBA", ph.size, NEON + (0,))
        gl.putalpha(glow.point(lambda v: int(v * 0.6)))
        c.alpha_composite(gl, (px, H - ph_h))
        c.alpha_composite(ph, (px, H - ph_h))
    else:
        big = fit(m.get("pao_crest"), 620)
        if big:
            a = big.getchannel("A").point(lambda v: int(v * 0.35))
            big.putalpha(a)
            c.alpha_composite(big, (W - big.width - 20, 380))

    glow_text(c, (60, 200), "MVP", font("black", 250), anchor="lt", radius=22)
    d = ImageDraw.Draw(c, "RGBA")
    d.text((66, 470), upper(m["first"]), font=font("semi", 48), fill=NEON_SOFT, anchor="lt")
    last = upper(m["last"])
    d.text((62, 520), last, font=shrink(d, last, "black", 96, 620), fill=WHITE, anchor="lt")

    sy = 650
    for val, lbl in m["stats"]:
        v = int(round(float(val or 0)))
        d.text((66, sy), str(v), font=font("black", 80), fill=WHITE, anchor="lt")
        d.text((72, sy + 80), lbl, font=font("semi", 28), fill=NEON_SOFT, anchor="lt")
        sy += 112

    # αποτέλεσμα κάτω
    bar_y = H - 120
    shape(c, "rounded_rectangle", (40, bar_y, W - 40, bar_y + 76), radius=38, fill=(2, 26, 11, 225), outline=NEON + (255,), width=3)
    res = upper(f"{m['home']} {m['score']} {m['away']}  |  {m['comp']}")
    ctext(d, W / 2, bar_y + 38, res, shrink(d, res, "xbold", 40, W - 160), anchor="mm")
    return c


def story(card):
    """Η κάρτα feed μέσα σε story 9:16, με το ίδιο φόντο."""
    s = background(SH, seed=91)
    scale = 0.96
    im = card.resize((int(W * scale), int(H * scale)), Image.LANCZOS)
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, im.width, im.height), radius=36, fill=255)
    x, y = (W - im.width) // 2, (SH - im.height) // 2 + 20
    shadow = Image.new("RGBA", (im.width + 80, im.height + 80), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((40, 40, im.width + 40, im.height + 40), radius=36, fill=(0, 0, 0, 170))
    s.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(24)), (x - 40, y - 28))
    s.paste(im, (x, y), mask)
    d = ImageDraw.Draw(s, "RGBA")
    d.rounded_rectangle((x, y, x + im.width, y + im.height), radius=36, outline=NEON + (255,), width=3)
    ctext(d, W / 2, y - 120, "TRIFILLAKIA.GR", font("black", 56), fill=WHITE)
    ctext(d, W / 2, y + im.height + 60, "@trifillakiagr", font("semi", 40), fill=NEON_SOFT)
    return s


def save(im, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.convert("RGB").save(path, "JPEG", quality=93, optimize=True)
    return path
