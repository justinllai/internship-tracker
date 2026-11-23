# ============================================================
# location_jobs.py — Resolve a location, search internships
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import Application, User
from schemas import JobSearchResponse, LocationResolveRequest, LocationResponse
from services import geo, job_search

router = APIRouter(tags=["location & jobs"])


# POST (not GET) on purpose: a GET would put ?lat=..&lng=.. or
# ?q=123+Main+St into the URL, and URLs get written to server
# access logs. A POST body doesn't.
@router.post("/location/resolve", response_model=LocationResponse)
def resolve_location(body: LocationResolveRequest, current_user: User = Depends(get_current_user)):
    try:
        if body.lat is not None and body.lng is not None:
            return geo.reverse(body.lat, body.lng)
        if body.q:
            return geo.forward(body.q)
    except geo.GeoError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    raise HTTPException(status_code=400, detail="Send either lat+lng or q")


@router.get("/jobs/search", response_model=JobSearchResponse)
def search_jobs(
    q: str = Query("software engineer", min_length=1, max_length=100),
    location: str = Query(..., min_length=2, max_length=120),
    radius_km: int = Query(40, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        results = job_search.search(q, location, radius_km)
    except job_search.JobSearchError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))

    # Mark postings this user already saved/applied to
    tracked = {
        (s, x) for s, x in db.query(Application.source, Application.external_id)
        .filter(Application.owner_id == current_user.id, Application.external_id.isnot(None))
    }
    enriched = [{**r, "already_tracked": (r["source"], r["external_id"]) in tracked} for r in results]
    return {"source": "adzuna", "location": location, "count": len(enriched), "results": enriched}
