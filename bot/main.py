"""Η αυτοματοποίηση: τρέχει κάθε 5 λεπτά (GitHub Actions).

  python -m bot run        έλεγχος και αναρτήσεις (χωρίς κλειδιά Meta: μόνο κάρτες στο out/)
  python -m bot preview    κάρτες δείγματα για όλα τα τμήματα στο out/preview/, χωρίς ανάρτηση
  python -m bot check      έλεγχος της σύνδεσης Meta (σελίδα, Instagram, δικαιώματα), χωρίς ανάρτηση
  python -m bot delete ID  οριστική διαγραφή αναρτήσεων Facebook (π.χ. διπλών)
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta

from . import basket, biolinks, captions, cards, flashscore as fs, meta, news, syndicate, wpl
from .config import (
    COMP_NAMES,
    FULLTIME_MAX_AGE_H,
    GAMEDAY_HOUR,
    GAMEDAY_MIN_LEAD_H,
    MVP_GIVE_UP_H,
    STANDINGS_FALLBACK_H,
    TEAMS,
    TZ,
)

ROOT = cards.ROOT
STATE = os.path.join(ROOT, "state.json")
OUT = os.path.join(ROOT, "out")
MAX_TRIES = 3
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
CI = os.environ.get("GITHUB_ACTIONS") == "true"
CLAIM_TTL = 15 * 60  # μια «κράτηση» ανάρτησης από άλλη εκτέλεση ισχύει 15 λεπτά


def log(*a):
    print(datetime.now(TZ).strftime("%d/%m %H:%M:%S"), *a, flush=True)


# --------------------------------------------------------------------------
# Κατάσταση (τι έχει ήδη αναρτηθεί)
# --------------------------------------------------------------------------


def load_state():
    try:
        with open(STATE, encoding="utf-8") as fh:
            st = json.load(fh)
    except (OSError, ValueError):
        st = {}
    st.setdefault("seeded", [])
    st.setdefault("posts", {})
    st.setdefault("pending", {})
    st.setdefault("news", {})
    st["news"].setdefault("last", 0)
    st["news"].setdefault("wait", {})
    st["news"].setdefault("recent", [])
    st.setdefault("synd", {})
    return st


def save_state(st):
    cutoff = time.time() - 120 * 86400
    st["posts"] = {k: v for k, v in st["posts"].items() if v.get("at", 0) > cutoff}
    with open(STATE, "w", encoding="utf-8") as fh:
        json.dump(st, fh, ensure_ascii=False, indent=1, sort_keys=True)


def is_done(st, key):
    p = st["posts"].get(key)
    if not p:
        return False
    # Άλλη εκτέλεση την ανεβάζει αυτή τη στιγμή.
    if p.get("claim") and p["claim"] != RUN_ID and time.time() - p.get("at", 0) < CLAIM_TTL:
        return True
    nets = p.get("nets", {})
    failed = [n for n, v in nets.items() if str(v).startswith("error")]
    if p.get("claim") and not nets:
        return False
    return not failed or p.get("tries", 0) >= MAX_TRIES


# --------------------------------------------------------------------------
# Συγχρονισμός της κατάστασης με το GitHub (δύο εκτελέσεις δεν ανεβάζουν το ίδιο)
# --------------------------------------------------------------------------


def _git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def _remote_state():
    if _git("fetch", "-q", "origin", "main").returncode != 0:
        return None
    r = _git("show", "origin/main:state.json")
    if r.returncode != 0:
        return {}
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {}


def merge_state(st, remote):
    """Ενώνει την κατάσταση του GitHub με την τοπική: για κάθε ανάρτηση κρατά την πιο πρόσφατη εγγραφή."""
    if not remote:
        return st
    for k, v in (remote.get("posts") or {}).items():
        mine = st["posts"].get(k)
        if mine is None or v.get("at", 0) > mine.get("at", 0):
            st["posts"][k] = v
    for k, v in (remote.get("pending") or {}).items():
        st["pending"].setdefault(k, v)
    st["seeded"] = sorted(set(st["seeded"]) | set(remote.get("seeded") or []))
    rn = remote.get("news") or {}
    st["news"]["last"] = max(st["news"]["last"], rn.get("last", 0))
    for k, v in (rn.get("wait") or {}).items():
        st["news"]["wait"].setdefault(k, v)
    recent = {a["nid"]: a for a in (rn.get("recent") or []) + st["news"]["recent"]}
    st["news"]["recent"] = sorted(recent.values(), key=lambda a: -a["nid"])[:40]
    rs = remote.get("synd") or {}
    if rs.get("since"):
        st["synd"]["since"] = min(x for x in (st["synd"].get("since"), rs["since"]) if x)
        st["synd"]["blocked"] = sorted(set(st["synd"].get("blocked") or []) | set(rs.get("blocked") or []))
        items = {i["guid"]: i for i in (rs.get("items") or []) + (st["synd"].get("items") or [])}
        st["synd"]["items"] = sorted(items.values(), key=lambda i: -i["ts"])[:30]
    return st


def sync_state(st, message="state"):
    """Αποθήκευση και push στο GitHub· αν άλλη εκτέλεση πρόλαβε, συγχώνευση και ξανά. True αν ανέβηκε."""
    if not CI:
        save_state(st)
        biolinks.write(st["news"]["recent"])
        return True
    for _ in range(6):
        merge_state(st, _remote_state())
        save_state(st)
        biolinks.write(st["news"]["recent"])
        _git("add", "state.json", "docs")
        if _git("diff", "--cached", "--quiet").returncode == 0:
            _git("reset", "-q", "--mixed", "origin/main")
            return True
        stamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
        _git("commit", "-q", "-m", f"{message}: {stamp}")
        if _git("push", "-q", "origin", "HEAD:main").returncode == 0:
            return True
        _git("reset", "-q", "--mixed", "origin/main")
        time.sleep(2)
    log("Δεν αποθηκεύτηκε η κατάσταση στο GitHub")
    return False


def claim(st, key):
    """«Κλείνει» μια ανάρτηση στο GitHub πριν γίνει, ώστε να μην την ανεβάσει και άλλη εκτέλεση.

    Το push είναι η κλειδαριά: αν άλλη εκτέλεση πρόλαβε να γράψει, το push απορρίπτεται,
    ξαναδιαβάζουμε την κατάσταση και βλέπουμε τη δική της κράτηση.
    """
    if not CI:
        return not is_done(st, key)
    for _ in range(6):
        remote = _remote_state()
        if remote is None:
            return False
        merge_state(st, remote)
        if is_done(st, key):
            return False
        prev = st["posts"].get(key, {})
        st["posts"][key] = {"at": time.time(), "nets": prev.get("nets", {}), "tries": prev.get("tries", 0), "claim": RUN_ID}
        save_state(st)
        _git("add", "state.json")
        _git("commit", "-q", "-m", f"claim {key}")
        if _git("push", "-q", "origin", "HEAD:main").returncode == 0:
            return True
        # Άλλη εκτέλεση έγραψε στο μεταξύ: πετάμε τη δική μας κράτηση και ξαναελέγχουμε.
        _git("reset", "-q", "--mixed", "origin/main")
        if prev:
            st["posts"][key] = prev
        else:
            st["posts"].pop(key, None)
        time.sleep(2)
    return False


# --------------------------------------------------------------------------
# Δεδομένα κάρτας
# --------------------------------------------------------------------------


def comp_name(name):
    base = name.split(" - ", 1)[0]
    return COMP_NAMES.get(base, base)


def round_label(title):
    """«Stoiximan Super League - Αγωνιστική ημέρα: 6» => («6η Αγωνιστική», «Αγωνιστική ημέρα: 6»)."""
    raw = title.split(" - ", 1)[1] if " - " in title else ""
    m = re.search(r"Αγωνιστική ημέρα:\s*(\d+)", raw)
    if m:
        return f"{m.group(1)}η Αγωνιστική", raw
    return raw, raw


def match_data(ev, team_key, details=True):
    team = TEAMS[team_key]
    pao_home = ev["home_id"] == team["fs"].split("/")[1]
    pao_away = ev["away_id"] == team["fs"].split("/")[1]
    cr = fs.crests(ev["id"])
    rnd, raw_round = round_label(fs.tournament_title(ev["id"]))
    m = dict(ev)
    m.update(
        {
            "team": team_key,
            "label": team["label"],
            "sport": team["sport"],
            "comp": comp_name(ev["comp"]),
            "round": rnd,
            "raw_round": raw_round,
            "home_crest": cards.crest_image(ev["home_id"], cr.get("home"), team["crest"] if pao_home else None),
            "away_crest": cards.crest_image(ev["away_id"], cr.get("away"), team["crest"] if pao_away else None),
            "goals": [],
            "venue": "",
        }
    )
    if details:
        s = fs.summary(ev["id"])
        m["goals"] = s["goals"]
        m["venue"] = s["venue"]
    return m


def pao_id(team_key):
    return TEAMS[team_key]["fs"].split("/")[1]


# --------------------------------------------------------------------------
# Αναρτήσεις
# --------------------------------------------------------------------------


def post(st, key, card, caption, dry, story_card=None, publisher=None):
    stamp = datetime.now(TZ).strftime("%Y%m%d-%H%M")
    safe = key.replace(":", "_")
    feed = cards.save(card, os.path.join(OUT, f"{stamp}_{safe}.jpg"))
    story = cards.save(story_card or cards.story(card), os.path.join(OUT, f"{stamp}_{safe}_story.jpg"))
    with open(os.path.join(OUT, f"{stamp}_{safe}.txt"), "w", encoding="utf-8") as fh:
        fh.write(caption)
    if dry:
        # Δοκιμή: δεν σημειώνεται ως αναρτημένο, ώστε να βγει κανονικά όταν μπουν τα κλειδιά Meta.
        log("ΔΟΚΙΜΗ (χωρίς ανάρτηση)", key)
        return
    if not claim(st, key):
        log("Ήδη αναρτημένο ή σε εξέλιξη από άλλη εκτέλεση:", key)
        return
    prev = st["posts"].get(key, {})
    nets = dict(prev.get("nets", {}))
    nets.update((publisher or meta.publish)(feed, story, caption, done=nets))
    st["posts"][key] = {"at": time.time(), "nets": nets, "tries": prev.get("tries", 0) + 1}
    log("ΑΝΑΡΤΗΣΗ", key, nets)
    sync_state(st, f"posted {key}")


def standings_rows(ev):
    rows = fs.standings(ev["tour_id"], ev["stage_id"])
    if not rows:
        return []
    # Αν η βαθμολογία έχει ομίλους (η θέση ξαναρχίζει από το 1), κρατάμε τον όμιλο της ομάδας μας.
    groups, cur = [], []
    for r in rows:
        if cur and r["rank"] <= cur[-1]["rank"]:
            groups.append(cur)
            cur = []
        cur.append(r)
    groups.append(cur)
    ids = {ev["home_id"], ev["away_id"]}
    return next((g for g in groups if any(r["id"] in ids for r in g)), [])


def run(dry=False):
    st = load_state()
    now = time.time()
    dry = dry or not meta.configured()
    if dry:
        log("Χωρίς κλειδιά Meta: οι κάρτες γράφονται μόνο στο out/ (δεν αναρτώνται).")

    for team_key, team in TEAMS.items():
        try:
            events = fs.team_events(team["fs"])
        except Exception as e:  # noqa: BLE001
            log("Σφάλμα Flashscore", team_key, e)
            continue
        if not events:
            log("Κανένας αγώνας / μη διαθέσιμο", team_key)
            continue

        if team_key not in st["seeded"]:
            # Πρώτη φορά: ό,τι έχει ήδη γίνει δεν αναρτάται.
            for ev in events:
                if ev["status"] in ("2", "3") or ev["start"] < now:
                    for kind in ("gd", "ft", "mvp", "tb"):
                        st["posts"][f"{kind}:{ev['id']}"] = {"at": now, "nets": {"seed": "ok"}}
            st["seeded"].append(team_key)
            log("Αρχικοποίηση", team_key, len(events), "αγώνες")
            continue

        for ev in events:
            if ev["stage"] in fs.OFF_STATES:
                continue
            # Πόλο Α1: αν το Flashscore δεν έχει ακόμα αποτέλεσμα, το παίρνουμε από το live της ΚΟΕ.
            if team_key == "waterpolo" and ev["status"] in ("1", "2") and ev["comp"].startswith("Α1") and ev["start"] < now:
                res = wpl.result(ev, ev["home_id"] == pao_id(team_key))
                if res:
                    ev.update(res, status="3")
                    log("Αποτέλεσμα από ΚΟΕ:", ev["home"], res["home_score"], "-", res["away_score"], ev["away"])
            # GAME DAY
            key = f"gd:{ev['id']}"
            if ev["status"] == "1" and not is_done(st, key):
                start = datetime.fromtimestamp(ev["start"], TZ)
                at = min(start.replace(hour=GAMEDAY_HOUR, minute=0, second=0), start - timedelta(hours=GAMEDAY_MIN_LEAD_H))
                if at.timestamp() <= now < ev["start"]:
                    m = match_data(ev, team_key)
                    post(st, key, cards.gameday(m), captions.gameday(m, team), dry)

            # FULL TIME
            key = f"ft:{ev['id']}"
            if ev["status"] == "3" and not is_done(st, key) and ev["start"] > now - (FULLTIME_MAX_AGE_H + 4) * 3600:
                if ev["home_score"] is None:
                    continue
                m = match_data(ev, team_key)
                post(st, key, cards.fulltime(m), captions.fulltime(m, team), dry)
                if team["sport"] == "basketball" and team_key == "basketball" and (basket.is_euroleague(ev) or basket.is_gbl(ev)):
                    st["pending"][f"mvp:{ev['id']}"] = {"team": team_key, "ev": ev, "since": now}
                if ev["tour_id"] and ev["stage_id"]:
                    st["pending"][f"tb:{ev['id']}"] = {"team": team_key, "ev": ev, "since": now, "raw_round": m["raw_round"], "round": m["round"]}

    try:
        syndicate.update(st["synd"], now, log=log)
    except Exception as e:  # noqa: BLE001
        log("Σφάλμα ροής bala24/totalbasket", e)

    try:
        run_news(st, now, dry)
    except Exception as e:  # noqa: BLE001
        log("Σφάλμα ειδήσεων", e)

    # MVP και βαθμολογίες που περιμένουν
    for key, p in list(st["pending"].items()):
        ev, team_key = p["ev"], p["team"]
        team = TEAMS[team_key]
        age_h = (now - p["since"]) / 3600
        try:
            if key.startswith("mvp:"):
                if is_done(st, key):
                    del st["pending"][key]
                    continue
                mv = basket.mvp(ev)
                if mv:
                    pao_home = ev["home_id"] == pao_id(team_key)
                    mv.update(
                        {
                            "label": team["label"],
                            "home": ev["home"],
                            "away": ev["away"],
                            "score": f"{ev['home_score']}-{ev['away_score']}",
                            "pao_crest": cards.crest_image(None, None, team["crest"]),
                            "pao_home": pao_home,
                            "comp_logo": ev.get("comp_logo"),
                            "tour_id": ev.get("tour_id"),
                        }
                    )
                    post(st, key, cards.mvp(mv), captions.mvp(mv, team), dry)
                    if is_done(st, key):
                        del st["pending"][key]
                elif age_h > MVP_GIVE_UP_H:
                    log("MVP: δεν βρέθηκαν στατιστικά", key)
                    del st["pending"][key]
            elif key.startswith("tb:"):
                if is_done(st, key):
                    del st["pending"][key]
                    continue
                finished = fs.round_finished(ev["tour_path"], p.get("raw_round"))
                if not p.get("raw_round"):
                    finished = age_h > 3
                if finished or age_h > STANDINGS_FALLBACK_H:
                    rows = standings_rows(ev)
                    if not rows or len(rows) < 3:
                        del st["pending"][key]
                        continue
                    m = {
                        "label": team["label"],
                        "comp": comp_name(ev["comp"]),
                        "round": p.get("round") and f"μετά την {p['round']}",
                        "rows": rows,
                        "pao_id": pao_id(team_key),
                        "sport": team["sport"],
                        "comp_logo": ev.get("comp_logo"),
                        "tour_id": ev.get("tour_id"),
                    }
                    post(st, key, cards.standings(m), captions.standings(m, team), dry)
                    if is_done(st, key):
                        del st["pending"][key]
        except Exception as e:  # noqa: BLE001
            log("Σφάλμα", key, e)

    sync_state(st)


def run_news(st, now, dry):
    """Νέα άρθρα του trifillakia.gr: κάρτα + story στο Instagram, link στο Facebook."""
    ns = st["news"]
    for item in ns["recent"]:
        if "itok=" not in item.get("thumb", ""):
            t = news.thumb_url(item.get("image", ""))
            if "itok=" in t:
                item["thumb"] = t
    home = news.latest_nid()
    if not ns["last"]:
        # Πρώτη φορά: ξεκινάμε από τώρα, χωρίς παλιά άρθρα.
        ns["last"] = home
        log("Ειδήσεις: αρχή από το άρθρο", home)
        # Η σελίδα του bio ξεκινά με τα πιο πρόσφατα άρθρα (χωρίς να αναρτηθούν).
        for nid in range(home, home - 80, -1):
            if len(ns["recent"]) >= 24:
                break
            status, url = news.probe(nid)
            if status == "ok" and news.wanted(url):
                a = news.article(nid, url)
                if a and a["title"]:
                    ns["recent"].append({k: a[k] for k in ("nid", "url", "title", "image", "label")})
        return
    # Άρθρα που ήταν κρυφά (403) ξαναελέγχονται για 2 ημέρες.
    candidates = [int(n) for n in ns["wait"] if now - ns["wait"][n] < 2 * 86400]
    ns["wait"] = {k: v for k, v in ns["wait"].items() if now - v < 2 * 86400}
    misses, nid = 0, ns["last"]
    while misses < news.LOOKAHEAD or nid < home:
        nid += 1
        status, url = news.probe(nid)
        if status == "ok":
            misses = 0
            ns["last"] = nid
            candidates.append(nid)
        elif status == "hidden":
            misses = 0
            ns["wait"].setdefault(str(nid), now)
        else:
            misses += 1
        if nid > home + 200:
            break
    for nid in sorted(set(candidates)):
        key = f"news:{nid}"
        if is_done(st, key):
            ns["wait"].pop(str(nid), None)
            continue
        status, url = news.probe(nid)
        if status != "ok":
            continue
        ns["wait"].pop(str(nid), None)
        if not news.wanted(url):
            continue
        a = news.article(nid, url)
        if not a or not a["title"]:
            continue
        post(
            st,
            key,
            cards.news_card(a),
            captions.news_ig(a),
            dry,
            story_card=cards.news_story(a),
            publisher=lambda f, sp, c, done, a=a: meta.publish_news(f, sp, c, a["url"], captions.news_fb(a), done=done),
        )
        if not dry:
            ns["recent"] = [x for x in ns["recent"] if x["nid"] != nid]
            item = {k: a[k] for k in ("nid", "url", "title", "image", "label")}
            item["thumb"] = news.thumb_url(a["image"])
            ns["recent"].insert(0, item)
            ns["recent"] = ns["recent"][:40]


def preview():
    """Κάρτες δείγματα: επόμενος αγώνας (GAME DAY), τελευταίο αποτέλεσμα (FULL TIME), βαθμολογία, MVP."""
    out = os.path.join(OUT, "preview")
    os.makedirs(out, exist_ok=True)
    only = sys.argv[2:] or list(TEAMS)
    for team_key in only:
        team = TEAMS[team_key]
        events = fs.team_events(team["fs"])
        nxt = next((e for e in events if e["status"] == "1" and e["stage"] not in fs.OFF_STATES), None)
        last = next((e for e in reversed(events) if e["status"] == "3" and e["home_score"] is not None), None)
        if nxt:
            m = match_data(nxt, team_key)
            cards.save(cards.gameday(m), os.path.join(out, f"{team_key}_gameday.jpg"))
            cards.save(cards.story(cards.gameday(m)), os.path.join(out, f"{team_key}_gameday_story.jpg"))
            open(os.path.join(out, f"{team_key}_gameday.txt"), "w", encoding="utf-8").write(captions.gameday(m, team))
        if last:
            m = match_data(last, team_key)
            cards.save(cards.fulltime(m), os.path.join(out, f"{team_key}_fulltime.jpg"))
            open(os.path.join(out, f"{team_key}_fulltime.txt"), "w", encoding="utf-8").write(captions.fulltime(m, team))
            rows = standings_rows(last)
            if len(rows) >= 3:
                sm = {"label": team["label"], "comp": comp_name(last["comp"]), "round": m["round"] and f"μετά την {m['round']}", "rows": rows, "pao_id": pao_id(team_key), "sport": team["sport"], "comp_logo": last.get("comp_logo"), "tour_id": last.get("tour_id")}
                cards.save(cards.standings(sm), os.path.join(out, f"{team_key}_standings.jpg"))
                open(os.path.join(out, f"{team_key}_standings.txt"), "w", encoding="utf-8").write(captions.standings(sm, team))
            if team_key == "basketball":
                mv = basket.mvp(last)
                if mv:
                    mv.update({"label": team["label"], "home": last["home"], "away": last["away"], "score": f"{last['home_score']}-{last['away_score']}", "pao_crest": cards.crest_image(None, None, team["crest"]), "comp_logo": last.get("comp_logo"), "tour_id": last.get("tour_id")})
                    cards.save(cards.mvp(mv), os.path.join(out, f"{team_key}_mvp.jpg"))
                    open(os.path.join(out, f"{team_key}_mvp.txt"), "w", encoding="utf-8").write(captions.mvp(mv, team))
        log("preview", team_key, "ok", "next:", nxt and nxt["home"] + "-" + nxt["away"], "last:", last and last["home"] + "-" + last["away"])


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "preview":
        preview()
    elif cmd == "check":
        meta.check()
    elif cmd == "delete":
        meta.delete([x for x in sys.argv[2:] for x in x.replace(",", " ").split()])
    else:
        run(dry=os.environ.get("DRY_RUN") == "1")


if __name__ == "__main__":
    main()
