"""Ειδήσεις του Ερασιτέχνη (pao1908.com: «Νέα», «Ανακοινώσεις», «Δελτία τύπου») → trifillakia.gr.

Κάθε άρθρο ξαναγράφεται από το Claude (άλλος τίτλος, άλλο κείμενο, ίδια γεγονότα), κρατά τη φωτογραφία
του pao1908 και μπαίνει στην ίδια ροή με bala24/totalbasket (docs/pao-feed.xml → Feeds του Drupal).
Από εκεί τα Παναθηναϊκά Νέα και το PAO Radio το παίρνουν μόνα τους.

Χωρίς ANTHROPIC_API_KEY δεν μπαίνει τίποτα (ποτέ αυτούσιο κείμενο).
"""
import html
import json
import os
import re
from datetime import datetime, timezone

import requests

API = "https://www.pao1908.com/wp-json/wp/v2/posts"
CATS = {1, 6, 7}  # Δελτία τύπου, ΝΕΑ, Ανακοινώσεις
START = datetime(2026, 10, 31, 22, 0, tzinfo=timezone.utc).timestamp()  # 1/11/2026 00:00 ώρα Ελλάδας
LOOKBACK = 7 * 86400
PER_RUN = 5  # πόσα ξαναγράφονται ανά εκτέλεση (το backfill μπαίνει σταδιακά)
MODEL = "claude-sonnet-5-5"  # Haiku αντέστρεψε σκορ (43-44 → «νίκη 44-43») στις 6/11

# Άθλημα του pao1908 → τμήμα (κατηγορία) του trifillakia, ονόματα όπως στο Drupal. Όλα τα άλλα → Ερασιτέχνης.
def section(sport):
    t = _plain(sport)
    if "βολει" in t:
        return "Βόλεϊ Γυναικών" if "γυναικ" in t else "Βολεϊ Ανδρών"
    if "μπασκετ γυναικ" in t:
        return "Μπάσκετ Γυναικών"
    if "πολο" in t.split() or t.startswith("πολο"):
        return "Πόλο"
    return DEFAULT_CAT


def _plain(text):
    import unicodedata
    t = unicodedata.normalize("NFD", (text or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


DEFAULT_CAT = "Ερασιτεχνης"

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
_s = requests.Session()
_s.headers.update({"User-Agent": UA})


def fetch(log=print):
    """Τα άρθρα των 3 κατηγοριών από 1/11 (ή της τελευταίας εβδομάδας), πιο παλιά πρώτα."""
    since = max(START, datetime.now(timezone.utc).timestamp() - LOOKBACK)
    after = datetime.fromtimestamp(since, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    posts = []
    for page in (1, 2, 3):
        try:
            r = _s.get(API, params={
                "after": after, "per_page": 100, "page": page,
                "_fields": "id,date_gmt,title,link,content,sport,cwp_category,cwp_featured_full",
            }, timeout=40)
        except requests.RequestException as e:
            log("pao1908: σφάλμα", repr(e)[:150])
            break
        if r.status_code != 200:
            if page == 1:
                log(f"pao1908: απάντησε {r.status_code}", r.text[:150].replace("\n", " "))
            break
        batch = r.json()
        posts += batch
        if len(batch) < 100:
            break
    out = []
    for p in posts:
        cats = {c.get("term_id") for c in p.get("cwp_category") or [] if isinstance(c, dict)}
        if not cats & CATS:
            continue
        sport = html.unescape(p.get("sport") or "").strip()
        out.append({
            "guid": f"pao1908.com:{p['id']}",
            "source": "pao1908.com",
            "category": section(sport),
            "orig_title": html.unescape(re.sub(r"<[^>]+>", "", p["title"]["rendered"])).strip(),
            "orig_body": p["content"]["rendered"],
            "sport": sport,
            "link": p["link"],
            "image": p.get("cwp_featured_full") or "",
            "ts": datetime.fromisoformat(p["date_gmt"]).replace(tzinfo=timezone.utc).timestamp(),
        })
    return sorted(out, key=lambda i: i["ts"])


PROMPT = """Είσαι συντάκτης του trifillakia.gr (site για τον Παναθηναϊκό). Ξαναγράψε την παρακάτω είδηση του ΠΑΟ (Ερασιτέχνης) με δικά σου λόγια.

Κανόνες:
- Νέος τίτλος, διαφορετικός από τον αρχικό, σύντομος και ειδησεογραφικός (όχι clickbait, χωρίς emoji, χωρίς εισαγωγικά γύρω του).
- Κείμενο με άλλη διατύπωση και σειρά προτάσεων, αλλά ΙΔΙΑ γεγονότα: ονόματα, σκορ, σετ, χρόνοι, θέσεις, ημερομηνίες, ώρες, τιμές εισιτηρίων ακριβώς όπως στο αρχικό. Μην προσθέσεις τίποτα που δεν γράφει.
- Σκορ και αποτελέσματα: γράψ' τα ΑΚΡΙΒΩΣ με την ίδια σειρά αριθμών (το «43-44» μένει «43-44»). Στο «Α – Β 43-44» νίκησε η Β (Α 43, Β 44). Αν δεν είναι σαφές ποιος νίκησε, μη γράψεις «νίκη»/«ήττα».
- Αν το αρχικό έχει λίστες, πίνακες αποτελεσμάτων, συνθέσεις ή πρόγραμμα αγώνων, κράτα τα όλα (μπορείς να τα μορφοποιήσεις ως <ul><li> ή <p> με <strong>).
- Περίπου ίδιο μήκος με το αρχικό. Αν το αρχικό είναι πολύ μικρό, γράψε τουλάχιστον 2 παραγράφους χωρίς να επινοήσεις στοιχεία.
- HTML μόνο με <p>, <strong>, <em>, <ul>, <li>, <br>. Χωρίς εικόνες, links, <h1>-<h6>.
- Στην πρώτη πρόταση να φαίνεται καθαρά το τμήμα/άθλημα του Παναθηναϊκού (π.χ. «η ομάδα βόλεϊ γυναικών», «το τμήμα πινγκ πονγκ», «η ακαδημία πάλης»), αν είναι γνωστό.
- Γλώσσα: ελληνικά, φυσικό αθλητικό ύφος.

- Κράτα το είδος του κειμένου: αφιέρωμα, «σαν σήμερα», μνήμη ή ιστορικό κείμενο μένει αφιέρωμα. Ο τίτλος ΔΕΝ το παρουσιάζει ως τωρινό γεγονός (π.χ. όχι «Πέθανε ο …» για κάποιον που έφυγε παλιότερα, αλλά «Θυμόμαστε τον …»). Αν δεν λέει έτος, μη βάλεις έτος.

- Υπότιτλος: μία πρόταση (έως ~200 χαρακτήρες) που συμπληρώνει τον τίτλο με το βασικό στοιχείο της είδησης, χωρίς να τον επαναλαμβάνει.
- Ετικέτες: 3 έως 5, ονόματα προσώπων, ομάδων/αντιπάλων, διοργανώσεων ή του αθλήματος που αναφέρει το κείμενο (π.χ. «Παναθηναϊκός», «Βόλεϊ Γυναικών», «Μαργαριτοπούλου»). Όχι γενικές λέξεις.

Δώσε την απάντηση με το εργαλείο save_article.

Ημερομηνία δημοσίευσης στο pao1908: {date}{old}
Άθλημα: {sport}
Αρχικός τίτλος: {title}
Αρχικό κείμενο:
{body}"""


def _clean_source(body):
    body = re.sub(r"<(script|style|iframe|figure)[^>]*>.*?</\1>", " ", body, flags=re.S | re.I)
    body = re.sub(r"<img[^>]*>", " ", body, flags=re.I)
    return re.sub(r"\n{3,}", "\n\n", body).strip()[:12000]


class ApiError(Exception):
    pass


def rewrite(item, key, log=print):
    date = datetime.fromtimestamp(item["ts"], timezone.utc).strftime("%d/%m/%Y")
    m = re.search(r"/uploads/(\d{4})/", item.get("image") or "")
    old = (f" (η φωτογραφία ανέβηκε το {m.group(1)}: πιθανότατα παλιό κείμενο που ξαναδημοσιεύτηκε, π.χ. αφιέρωμα)"
           if m and int(m.group(1)) < datetime.fromtimestamp(item["ts"], timezone.utc).year else "")
    prompt = (PROMPT.replace("{sport}", item["sport"] or "-").replace("{title}", item["orig_title"])
              .replace("{date}", date).replace("{old}", old).replace("{body}", _clean_source(item["orig_body"])))
    tool = {"name": "save_article", "description": "Αποθηκεύει το ξαναγραμμένο άρθρο.", "input_schema": {
        "type": "object", "required": ["title", "body"], "properties": {
            "title": {"type": "string", "description": "Νέος τίτλος"},
            "body": {"type": "string", "description": "Κείμενο σε HTML"},
            "subtitle": {"type": "string", "description": "Υπότιτλος, μία πρόταση"},
            "tags": {"type": "array", "items": {"type": "string"}, "description": "3-5 ετικέτες"}}}}
    try:
        r = requests.post("https://api.anthropic.com/v1/messages", timeout=120, headers={
            "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json",
        }, json={"model": MODEL, "max_tokens": 4000, "tools": [tool],
                 "tool_choice": {"type": "auto"},
                 "messages": [{"role": "user", "content": prompt}]})
    except requests.RequestException as e:
        log("pao1908: σφάλμα Claude", repr(e)[:150])
        return None
    if r.status_code != 200:
        log(f"pao1908: Claude {r.status_code}", r.text[:200].replace("\n", " "))
        raise ApiError(r.status_code)
    content = r.json().get("content", [])
    data = next((b.get("input") for b in content if b.get("type") == "tool_use"), None)
    if data is None:  # χωρίς εργαλείο: JSON μέσα στο κείμενο
        text = "".join(b.get("text", "") for b in content if b.get("type") == "text")
        m = re.search(r"\{.*\}", text, re.S)
        try:
            data = json.loads(m.group(0)) if m else None
        except ValueError:
            data = None
    if not isinstance(data, dict) or not str(data.get("title", "")).strip() or len(re.sub(r"<[^>]+>", "", str(data.get("body", "")))) < 80:
        log("pao1908: άκυρη απάντηση Claude για", item["orig_title"], str(data)[:150])
        return None
    title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", str(data["title"]))).strip().strip("«»\"")
    body = str(data["body"]).strip()
    body += f'<p><em>Πηγή: <a href="{html.escape(item["link"])}" target="_blank" rel="noopener">pao1908.com</a></em></p>'
    sub = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", str(data.get("subtitle") or ""))).strip()
    tags = [re.sub(r"\s+", " ", str(t)).strip().lstrip("#") for t in (data.get("tags") or []) if str(t).strip()]
    return title, body, sub, list(dict.fromkeys(tags))[:5]


SCORE = re.compile(r"(?<![\d:/])(?<!\d[.,])(\d{1,3})\s*[-–]\s*(\d{1,3})(?![\d:/]|[.,]\d)")


def _scores(htm):
    t = html.unescape(re.sub(r"<[^>]+>", " ", htm))
    return {f"{a}-{b}" for a, b in SCORE.findall(t)}


def checked_rewrite(item, key, log=print):
    """Ξαναγράψιμο + έλεγχος: κάθε σκορ του αρχικού πρέπει να υπάρχει ίδιο (ίδια σειρά) στο νέο κείμενο."""
    want = _scores(item["orig_title"] + " " + item["orig_body"])
    for _ in range(2):
        res = rewrite(item, key, log)
        if not res:
            return None
        got = _scores(res[0] + " " + res[1] + " " + res[2])
        missing = want - got
        flipped = {s for s in got - want if "-".join(reversed(s.split("-"))) in want}
        if not missing and not flipped:
            return res
        log("pao1908: σκορ δεν ταιριάζει, ξανά →", item["orig_title"], sorted(missing), sorted(flipped))
    return None


def candidates(have, existing, same_story, log=print):
    """Νέα άρθρα, ξαναγραμμένα (έως PER_RUN), έτοιμα για τη ροή. existing = άρθρα του trifillakia."""
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    posts = [p for p in fetch(log) if p["guid"] not in have]
    log(f"Ροή trifillakia: pao1908.com νέα {len(posts)}")
    if not posts:
        return []
    if not key:
        log("pao1908: λείπει το ANTHROPIC_API_KEY, δεν μπαίνει τίποτα")
        return []
    out = []
    for p in posts:
        if len(out) >= PER_RUN:
            break
        near = [d for d in existing if not d["ts"] or abs(d["ts"] - p["ts"]) < 36 * 3600]
        if any(same_story(p["orig_title"], d) for d in near):
            log("Ροή trifillakia: υπάρχει ήδη →", p["orig_title"])
            out.append(dict(p, skip=True))
            continue
        try:
            res = checked_rewrite(p, key, log)
        except ApiError:
            break  # σφάλμα API (κλειδί, μοντέλο, όριο): σταματάμε ως την επόμενη εκτέλεση
        if not res:
            continue
        title, body, sub, tags = res
        out.append({k: p[k] for k in ("guid", "source", "category", "link", "image", "ts")}
                   | {"title": title, "body": body, "subtitle": sub, "tags": tags})
    return out
