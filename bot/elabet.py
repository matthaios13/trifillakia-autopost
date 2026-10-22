"""Ροή ELABET για το trifillakia.gr (importer «ELABET άρθρα» του Drupal Feeds).

Τα άρθρα ELABET μπαίνουν από το email στο bala24 (ποδόσφαιρο + γενικά) και στο totalbasket (μπάσκετ),
και καθένα δίνει τη δική του ροή (?bala_em_feed=1&own=1). Εδώ τις ενώνουμε φρέσκιες (χωρίς cache)
και μετατρέπουμε τα emoji: η βάση του trifillakia (utf8, όχι utf8mb4) αρνείται χαρακτήρες 4 byte.
"""
import html
import os
import re
import time

import requests

from .cards import ROOT
from .flashscore import UA

FEED = os.path.join(ROOT, "docs", "elabet-feed.xml")
SOURCES = ("https://bala24.gr/?bala_em_feed=1&own=1", "https://totalbasket.gr/?bala_em_feed=1&own=1")


def _bmp(text, plain=False):
    if plain:
        return re.sub(r"\s{2,}", " ", "".join(c for c in text if ord(c) <= 0xFFFF and c != "️")).strip()
    return "".join(c if ord(c) <= 0xFFFF else f"&#{ord(c)};" for c in text)


def _clean_item(item):
    item = re.sub(r"<title>(.*?)</title>", lambda m: "<title>" + _bmp(m.group(1), plain=True) + "</title>", item, flags=re.S)
    return _bmp(item)  # στο υπόλοιπο (κείμενο σε CDATA) οι οντότητες μένουν ως HTML και ο browser δείχνει τα emoji


def update(log=print):
    items, ok = [], 0
    for url in SOURCES:
        try:
            r = requests.get(url, params={"nc": int(time.time())}, headers={"User-Agent": UA}, timeout=30)
        except requests.RequestException:
            continue
        if r.status_code != 200 or "<rss" not in r.text:
            continue
        ok += 1
        items += re.findall(r"<item>.*?</item>", r.text, re.S)
    if ok < len(SOURCES):
        log("ELABET: δεν απάντησαν όλες οι πηγές, η ροή μένει ως έχει")
        return False

    def pub(it):
        m = re.search(r"<pubDate>(.*?)</pubDate>", it)
        try:
            from email.utils import parsedate_to_datetime

            return parsedate_to_datetime(html.unescape(m.group(1))).timestamp() if m else 0
        except (TypeError, ValueError):
            return 0

    items = sorted({re.search(r"<guid[^>]*>(.*?)</guid>", i).group(1) if re.search(r"<guid[^>]*>(.*?)</guid>", i) else i: i for i in items}.values(), key=pub, reverse=True)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>'
        "<title>Trifillakia — ELABET (bala24 + totalbasket)</title><link>https://www.trifillakia.gr</link><description>ELABET</description>"
        + "".join(_clean_item(i) for i in items[:30])
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
    return True
