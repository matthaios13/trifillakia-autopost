"""Κανάλι Viber του trifillakia: κάθε είδηση που ανεβαίνει στο Instagram/Facebook πάει και εδώ (18/11).

Viber Channels Post API: https://chatapi.viber.com/pa/post με το token του καναλιού (secret VIBER_TOKEN,
το βρίσκει ο Superadmin στο Viber του κινητού: Κανάλι → Ρυθμίσεις → Developer Tools). Το «from» είναι
ο Superadmin του καναλιού (get_account_info).
"""
import os

import requests

API = "https://chatapi.viber.com/pa"
WEBHOOK = "https://bala24.gr/feed/"
_from = {}


def token():
    return os.environ.get("VIBER_TOKEN", "").strip()


def configured():
    return bool(token())


def _call(method, payload, log=print):
    try:
        r = requests.post(f"{API}/{method}", json=dict(payload, auth_token=token()),
                          headers={"X-Viber-Auth-Token": token()}, timeout=30)
        d = r.json()
    except (requests.RequestException, ValueError) as e:
        log("Viber: σφάλμα", method, repr(e)[:150])
        return None
    if d.get("status") != 0:
        log("Viber:", method, d.get("status"), d.get("status_message"))
        return None
    return d


def sender(log=print):
    """Το id του Superadmin (όποιος «υπογράφει» τις αναρτήσεις του καναλιού)."""
    if "id" not in _from:
        d = _call("get_account_info", {}, log) or {}
        if d and not d.get("webhook"):
            # Το Viber δεν δέχεται αναρτήσεις χωρίς webhook (webhookNotSet). Δεν χρειαζόμαστε ειδοποιήσεις:
            # αρκεί μια δική μας διεύθυνση που απαντά 200 σε POST (το RSS του bala24).
            w = _call("set_webhook", {"url": WEBHOOK, "send_name": False, "send_photo": False}, log)
            log("Viber: webhook", "ορίστηκε" if w else "απέτυχε", WEBHOOK)
        admins = [m for m in d.get("members", []) if m.get("role") == "superadmin"] or d.get("members", [])
        _from["id"] = admins[0]["id"] if admins else ""
        if _from["id"]:
            log("Viber: κανάλι", d.get("name"), "| αποστολέας", admins[0].get("name"))
    return _from["id"]


def publish_news(a, done=None, log=print):
    """Ανάρτηση άρθρου (φωτογραφία + τίτλος + link). Επιστρέφει {'vb': message_token} ή {}."""
    if not configured() or (done or {}).get("vb"):
        return {}
    frm = sender(log)
    if not frm:
        return {}
    label = (a.get("label") or "").strip()
    desc = (a.get("description") or "").strip()
    parts = [f"☘ {label}" if label else "", a["title"].strip(), desc[:300] if desc and desc != a["title"].strip() else "", a["url"]]
    text = "\n\n".join(x for x in parts if x)
    text = text.strip()[:760]
    if a.get("image"):
        d = _call("post", {"from": frm, "type": "picture", "text": text, "media": a["image"], "thumbnail": a.get("thumb") or a["image"]}, log)
    else:
        d = None
    if not d:  # χωρίς φωτογραφία ή αν απέτυχε η φωτογραφία: σκέτο κείμενο με link
        d = _call("post", {"from": frm, "type": "text", "text": text}, log)
    return {"vb": str(d.get("message_token"))} if d else {}


def publish_show(v, text, log=print):
    """Προγραμματισμένη εκπομπή στο YouTube (23/11): thumbnail + κείμενο με το link. {'vb': token} ή {}."""
    if not configured():
        return {}
    frm = sender(log)
    if not frm:
        return {}
    text = text.strip()[:760]
    d = _call("post", {"from": frm, "type": "picture", "text": text, "media": v["image"], "thumbnail": v["image"]}, log) if v.get("image") else None
    if not d:
        d = _call("post", {"from": frm, "type": "text", "text": text}, log)
    return {"vb": str(d.get("message_token"))} if d else {}


def check(log=print):
    """Έλεγχος σύνδεσης (χωρίς ανάρτηση): όνομα καναλιού, συνδρομητές, ποιος θα «υπογράφει»."""
    if not configured():
        log("Viber: λείπει το VIBER_TOKEN")
        return
    d = _call("get_account_info", {}, log)
    if not d:
        return
    sa = [m.get("name") for m in d.get("members", []) if m.get("role") == "superadmin"]
    log("Viber OK: κανάλι", d.get("name"), "| συνδρομητές", d.get("subscribers_count"),
        "| superadmins", sa, "| webhook", bool(d.get("webhook")), "| uri", d.get("uri"))
