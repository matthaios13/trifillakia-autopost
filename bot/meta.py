"""Αναρτήσεις μέσω Meta Graph API: Facebook σελίδα (post + story) και Instagram (post + story).

Οι εικόνες ανεβαίνουν πρώτα στη σελίδα Facebook· το Instagram τις παίρνει από εκεί (θέλει δημόσιο URL).
Μεταβλητές περιβάλλοντος: META_TOKEN, FB_PAGE_ID, IG_USER_ID.
"""
import os
import time

import requests

GRAPH = "https://graph.facebook.com/v23.0"


class MetaError(Exception):
    pass


def configured():
    return all(os.environ.get(k) for k in ("META_TOKEN", "FB_PAGE_ID", "IG_USER_ID"))


def _token():
    return os.environ["META_TOKEN"]


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
    ig = os.environ["IG_USER_ID"]
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
