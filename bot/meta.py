"""Αναρτήσεις μέσω Meta Graph API: Facebook σελίδα (post + story) και Instagram (post + story).

Οι εικόνες ανεβαίνουν πρώτα στη σελίδα Facebook· το Instagram τις παίρνει από εκεί (θέλει δημόσιο URL).
Μεταβλητές περιβάλλοντος: META_TOKEN, FB_PAGE_ID και προαιρετικά IG_USER_ID (αλλιώς βρίσκεται από τη σελίδα).
"""
import os
import time

import requests

GRAPH = "https://graph.facebook.com/v23.0"


class MetaError(Exception):
    pass


def configured():
    return all(os.environ.get(k) for k in ("META_TOKEN", "FB_PAGE_ID"))


_ig = {}


def ig_id():
    """Το Instagram Business ID: από το IG_USER_ID ή από τη συνδεδεμένη σελίδα."""
    if os.environ.get("IG_USER_ID"):
        return os.environ["IG_USER_ID"]
    if "id" not in _ig:
        r = requests.get(
            f"{GRAPH}/{os.environ['FB_PAGE_ID']}",
            params={"fields": "instagram_business_account", "access_token": _token()},
            timeout=30,
        )
        _ig["id"] = (_check(r).get("instagram_business_account") or {}).get("id")
        if not _ig["id"]:
            raise MetaError("Η σελίδα δεν έχει συνδεδεμένο Instagram Business λογαριασμό")
    return _ig["id"]


def check():
    """Έλεγχος σύνδεσης χωρίς ανάρτηση: σελίδα, Instagram, δικαιώματα token."""
    page = _check(requests.get(f"{GRAPH}/{os.environ['FB_PAGE_ID']}", params={"fields": "name,instagram_business_account", "access_token": _token()}, timeout=30))
    print("Σελίδα Facebook:", page.get("name"), page.get("id"))
    ig = ig_id()
    acc = _check(requests.get(f"{GRAPH}/{ig}", params={"fields": "username,followers_count", "access_token": _token()}, timeout=30))
    print("Instagram:", "@" + str(acc.get("username")), ig, "followers:", acc.get("followers_count"))
    print("Token σελίδας:", "ναι" if _token() != os.environ["META_TOKEN"] else "ΟΧΙ (θα αποτύχουν οι αναρτήσεις)")
    perms = _check(requests.get(f"{GRAPH}/me/permissions", params={"access_token": os.environ["META_TOKEN"]}, timeout=30)).get("data", [])
    print("Δικαιώματα:", ", ".join(p["permission"] for p in perms if p.get("status") == "granted"))
    need = {"pages_manage_posts", "pages_read_engagement", "instagram_basic", "instagram_content_publish"}
    missing = need - {p["permission"] for p in perms if p.get("status") == "granted"}
    print("Λείπουν:", ", ".join(sorted(missing)) if missing else "τίποτα — όλα εντάξει")
    lim = _check(requests.get(f"{GRAPH}/{ig}/content_publishing_limit", params={"fields": "quota_usage,config", "access_token": _token()}, timeout=30))
    print("Όριο αναρτήσεων IG (24ω):", lim.get("data"))


_page_token = {}


def _token():
    """Token σελίδας (οι αναρτήσεις γίνονται ως σελίδα)· βγαίνει από τον token του χρήστη συστήματος."""
    if "t" not in _page_token:
        r = requests.get(
            f"{GRAPH}/{os.environ['FB_PAGE_ID']}",
            params={"fields": "access_token", "access_token": os.environ["META_TOKEN"]},
            timeout=30,
        )
        try:
            _page_token["t"] = r.json().get("access_token") or os.environ["META_TOKEN"]
        except ValueError:
            _page_token["t"] = os.environ["META_TOKEN"]
    return _page_token["t"]


def _check(r):
    try:
        data = r.json()
    except ValueError:
        raise MetaError(f"HTTP {r.status_code}: {r.text[:300]}")
    if r.status_code != 200 or "error" in data:
        raise MetaError(str(data.get("error", data))[:500])
    return data


def _upload_photo(path, caption=None, published=True):
    page = os.environ["FB_PAGE_ID"]
    data = {"access_token": _token(), "published": "true" if published else "false"}
    if caption:
        data["caption"] = caption
    if not published:
        data["temporary"] = "true"
    with open(path, "rb") as fh:
        r = requests.post(f"{GRAPH}/{page}/photos", data=data, files={"source": ("card.jpg", fh, "image/jpeg")}, timeout=120)
    return _check(r)


def _photo_url(photo_id):
    r = requests.get(f"{GRAPH}/{photo_id}", params={"fields": "images", "access_token": _token()}, timeout=30)
    images = _check(r).get("images") or []
    if not images:
        raise MetaError("Δεν βρέθηκε URL της εικόνας στο Facebook")
    return max(images, key=lambda i: i.get("width", 0))["source"]


def _ig_publish(params):
    ig = ig_id()
    params["access_token"] = _token()
    c = _check(requests.post(f"{GRAPH}/{ig}/media", data=params, timeout=60))
    cid = c["id"]
    for _ in range(20):
        st = _check(requests.get(f"{GRAPH}/{cid}", params={"fields": "status_code", "access_token": _token()}, timeout=30))
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") == "ERROR":
            raise MetaError("Το Instagram απέρριψε την εικόνα")
        time.sleep(3)
    return _check(requests.post(f"{GRAPH}/{ig}/media_publish", data={"creation_id": cid, "access_token": _token()}, timeout=60))["id"]


def publish(feed_path, story_path, caption, done=None):
    """Ανεβάζει σε όσα δίκτυα δεν έχουν ήδη γίνει (done). Επιστρέφει {δίκτυο: id ή 'error: ...'}."""
    done = dict(done or {})
    out = {}

    def ok(net):
        return net in done and not str(done[net]).startswith("error")

    feed_url = None
    if not ok("fb"):
        try:
            res = _upload_photo(feed_path, caption=caption, published=True)
            out["fb"] = res.get("post_id") or res["id"]
            feed_url = _photo_url(res["id"])
        except Exception as e:  # noqa: BLE001
            out["fb"] = f"error: {e}"
    if not ok("ig"):
        try:
            if not feed_url:
                feed_url = _photo_url(_upload_photo(feed_path, published=False)["id"])
            out["ig"] = _ig_publish({"image_url": feed_url, "caption": caption})
        except Exception as e:  # noqa: BLE001
            out["ig"] = f"error: {e}"
    if story_path and not (ok("igs") and ok("fbs")):
        try:
            sp = _upload_photo(story_path, published=False)
            if not ok("igs"):
                try:
                    out["igs"] = _ig_publish({"image_url": _photo_url(sp["id"]), "media_type": "STORIES"})
                except Exception as e:  # noqa: BLE001
                    out["igs"] = f"error: {e}"
            if not ok("fbs"):
                try:
                    r = requests.post(
                        f"{GRAPH}/{os.environ['FB_PAGE_ID']}/photo_stories",
                        data={"photo_id": sp["id"], "access_token": _token()},
                        timeout=60,
                    )
                    out["fbs"] = _check(r).get("post_id", "ok")
                except Exception as e:  # noqa: BLE001
                    out["fbs"] = f"error: {e}"
        except Exception as e:  # noqa: BLE001
            out.setdefault("igs", f"error: {e}")
            out.setdefault("fbs", f"error: {e}")
    return out
