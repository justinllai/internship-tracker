# ============================================================
# job_search.py — Find open internships near a location
# ------------------------------------------------------------
# Source: the Adzuna jobs API (free developer key).
#
# Why Adzuna and not LinkedIn/Indeed?
#   - LinkedIn and Indeed have no public job-search API, and
#     scraping them violates their Terms of Service (and breaks
#     whenever their HTML changes).
#   - Adzuna aggregates many boards, has an official free API,
#     and supports "near <place> within <N> km" natively.
#   - Adzuna's terms require attribution, so the Jobs page shows
#     "Jobs by Adzuna".
#
# Why not silently fall back to another source if keys are
# missing? We originally planned to fall back to The Muse, but
# its API now returns 404. A silent fallback also hides
# misconfiguration, so we fail loudly with a clear 503 instead.
# ============================================================

import re
import threading
import time
from datetime import datetime
from typing import Optional

import httpx

import config


class JobSearchError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


# "intern", "interns", "internship", "co-op", "coop" as WHOLE words.
# \b = word boundary, so "internal" and "international" don't match.
INTERN_TITLE = re.compile(r"\b(intern|interns|internship|internships|co-?op)\b", re.IGNORECASE)

_TAG = re.compile(r"<[^>]+>")


def _strip_html(text: Optional[str]) -> str:
    # Adzuna wraps matched keywords in <strong> tags. We render text,
    # not HTML, in React (which also escapes it), but strip anyway.
    return _TAG.sub("", text or "").strip()


def _salary(r: dict) -> Optional[str]:
    lo, hi = r.get("salary_min"), r.get("salary_max")
    if not lo and not hi:
        return None
    fmt = lambda n: f"${int(n):,}"
    text = f"{fmt(lo)}–{fmt(hi)}" if lo and hi and int(lo) != int(hi) else fmt(lo or hi)
    # salary_is_predicted == "1" means Adzuna estimated it
    return text + (" (est.)" if str(r.get("salary_is_predicted")) == "1" else "")


def _parse_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def normalize(r: dict) -> dict:
    """Turn one Adzuna result into OUR shape (so the frontend never
    depends on a third party's field names)."""
    return {
        "external_id": str(r.get("id")),
        "title": _strip_html(r.get("title")),
        "company": (r.get("company") or {}).get("display_name") or "Unknown company",
        "location": (r.get("location") or {}).get("display_name") or "",
        "url": r.get("redirect_url") or "",
        "posted_at": _parse_date(r.get("created")),
        "description": _strip_html(r.get("description"))[:300] or None,
        "salary": _salary(r),
        "source": "adzuna",
    }


# ---------- 10-minute cache ----------
# The same search (e.g. "software" near "San Jose, CA") is common;
# caching saves our free API quota and makes repeat loads instant.
_CACHE_TTL = 600
_cache: dict = {}
_cache_lock = threading.Lock()


def _fetch_adzuna(params: dict) -> dict:
    """The ONLY function that touches the network (tests mock it)."""
    url = f"https://api.adzuna.com/v1/api/jobs/{config.ADZUNA_COUNTRY}/search/1"
    try:
        resp = httpx.get(url, params=params, timeout=10.0)
    except httpx.HTTPError as e:
        raise JobSearchError("The job search service didn't respond. Try again in a moment.") from e
    data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    if resp.status_code in (401, 403) or data.get("exception") == "AUTH_FAIL":
        raise JobSearchError("Job search is misconfigured on the server (Adzuna credentials rejected).", 503)
    if resp.status_code >= 400:
        raise JobSearchError(f"Job search failed (upstream status {resp.status_code}).")
    return data


def search(query: str, location: str, radius_km: int) -> list:
    if not config.jobs_enabled():
        raise JobSearchError(
            "Job search isn't configured on this server yet. Add ADZUNA_APP_ID and ADZUNA_APP_KEY.", 503
        )

    key = (query.lower().strip(), location.lower().strip(), radius_km)
    now = time.monotonic()
    with _cache_lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < _CACHE_TTL:
            return hit[1]

    data = _fetch_adzuna({
        "app_id": config.ADZUNA_APP_ID,
        "app_key": config.ADZUNA_APP_KEY,
        "what": query,
        "what_or": "intern internship co-op",          # must contain at least one
        "what_exclude": "senior staff principal director manager",
        "where": location,
        "distance": radius_km,                           # Adzuna uses kilometres
        "max_days_old": 60,
        "results_per_page": 50,
        "sort_by": "date",
    })

    results = [normalize(r) for r in data.get("results", [])]
    # Second safety net: keep only titles that really say intern/co-op
    results = [r for r in results if INTERN_TITLE.search(r["title"]) and r["url"]]

    with _cache_lock:
        _cache[key] = (now, results)
        # keep the cache from growing forever
        if len(_cache) > 200:
            oldest = min(_cache, key=lambda k: _cache[k][0])
            _cache.pop(oldest, None)
    return results
