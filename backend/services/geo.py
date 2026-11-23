# ============================================================
# geo.py — Turn coordinates or an address into "City, ST"
# ------------------------------------------------------------
# Uses OpenStreetMap's free Nominatim geocoder.
#
# Privacy pipeline (why this is "safe"):
#   1. Coordinates are rounded to 2 decimals (~1.1 km) BEFORE
#      they're sent anywhere — Nominatim never sees a precise
#      position. (The browser already rounded too.)
#   2. We return ONLY city + state. Street, house number, ZIP
#      and coordinates from the response are thrown away.
#   3. Nothing here is written to the database or logged.
#
# Being a good API citizen (Nominatim's usage policy):
#   - Identify ourselves with a User-Agent.
#   - Max 1 request per second  → a lock + timestamp throttle.
#   - Cache results             → small in-memory LRU cache.
#   - No search-as-you-type     → we only geocode on submit.
# ============================================================

import hashlib
import threading
import time
from collections import OrderedDict
from typing import Optional

import httpx

import config

NOMINATIM = "https://nominatim.openstreetmap.org"


class GeoError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


# ---------- tiny LRU cache ----------
# OrderedDict remembers insertion order; moving a key to the end
# on each hit and popping from the front when full = "least
# recently used" eviction.
_CACHE_MAX = 500
_cache: "OrderedDict[str, dict]" = OrderedDict()
_cache_lock = threading.Lock()


def _cache_get(key):
    with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
    return None


def _cache_put(key, value):
    with _cache_lock:
        _cache[key] = value
        _cache.move_to_end(key)
        while len(_cache) > _CACHE_MAX:
            _cache.popitem(last=False)


# ---------- 1 request/second throttle ----------
_rate_lock = threading.Lock()
_last_call = 0.0


def _get_json(path: str, params: dict):
    """The ONLY function that touches the network (tests mock it)."""
    global _last_call
    with _rate_lock:
        wait = 1.0 - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()
    try:
        resp = httpx.get(
            f"{NOMINATIM}{path}",
            params=params,
            headers={"User-Agent": config.GEOCODER_USER_AGENT},
            timeout=8.0,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        raise GeoError("The location service is unavailable right now. Try typing your city.", 502) from e


def _to_place(address: dict) -> dict:
    """Keep only city + state from Nominatim's address breakdown."""
    city = (address.get("city") or address.get("town") or address.get("village")
            or address.get("hamlet") or address.get("county"))
    if not city:
        raise GeoError("Couldn't find a city for that location.", 404)
    # "ISO3166-2-lvl4": "US-CA" → "CA"; fall back to full state name
    iso = address.get("ISO3166-2-lvl4") or ""
    state = iso.split("-", 1)[1] if "-" in iso else address.get("state")
    label = f"{city}, {state}" if state else city
    return {"label": label, "city": city, "state": state}


def reverse(lat: float, lng: float) -> dict:
    lat, lng = round(lat, 2), round(lng, 2)     # privacy: ~1.1 km
    key = f"r:{lat},{lng}"
    if (hit := _cache_get(key)) is not None:
        return hit
    data = _get_json("/reverse", {
        "format": "jsonv2", "lat": lat, "lon": lng,
        "zoom": 10,            # 10 = city level; we don't ask for street detail
        "addressdetails": 1,
    })
    if not data or "address" not in data:
        raise GeoError("Couldn't find a city for that location.", 404)
    place = _to_place(data["address"])
    _cache_put(key, place)
    return place


def forward(query: str, country: Optional[str] = None) -> dict:
    q = " ".join(query.split())        # normalize whitespace
    if len(q) < 2:
        raise GeoError("Enter a city, ZIP code, or address.", 400)
    country = country or config.ADZUNA_COUNTRY
    # Hash the key: the typed text might be a home address, and we
    # don't want raw addresses sitting in server memory as cache keys.
    key = "f:" + hashlib.sha256(f"{country}:{q.lower()}".encode()).hexdigest()
    if (hit := _cache_get(key)) is not None:
        return hit
    results = _get_json("/search", {
        "format": "jsonv2", "q": q, "countrycodes": country,
        "addressdetails": 1, "limit": 1,
    })
    if not results:
        raise GeoError(f"We couldn't find \"{q}\". Try a city name or ZIP code.", 404)
    place = _to_place(results[0].get("address", {}))
    _cache_put(key, place)
    return place
