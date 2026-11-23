# ============================================================
# applications.py — CRUD for internship applications
# Same ownership rule as before on EVERY query:
#   filter(owner_id == current_user.id)
# so user A can never read/edit user B's rows, even by guessing ids.
# ============================================================

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from database import get_db
from deps import get_current_user
from models import Application, User, utcnow
from schemas import ApplicationCreate, ApplicationResponse, ApplicationUpdate

router = APIRouter(prefix="/applications", tags=["applications"])


def _get_owned(db: Session, application_id: int, user: User) -> Application:
    app = (db.query(Application)
           .filter(Application.id == application_id, Application.owner_id == user.id)
           .first())
    if not app:
        # 404 (not 403) for other people's rows too — don't even
        # confirm that the id exists.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return app


@router.post("", response_model=ApplicationResponse)
def create_application(application: ApplicationCreate, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    data = application.model_dump()

    # Saving the same posting twice (double click on "Save")?
    if data.get("source") and data.get("external_id"):
        dup = (db.query(Application)
               .filter(Application.owner_id == current_user.id,
                       Application.source == data["source"],
                       Application.external_id == data["external_id"])
               .first())
        if dup:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="You're already tracking this posting")

    new_application = Application(**data, owner_id=current_user.id)
    if new_application.status != "Saved":
        new_application.applied_at = utcnow()
    if new_application.track_email:
        new_application.track_email_since = utcnow()
    db.add(new_application)
    db.commit()
    db.refresh(new_application)
    return new_application


@router.get("", response_model=List[ApplicationResponse])
def get_applications(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # selectinload = fetch every application's emails in ONE extra
    # query, instead of one query per application (the "N+1 query"
    # problem that makes list pages slow).
    return (db.query(Application)
            .options(selectinload(Application.email_events))
            .filter(Application.owner_id == current_user.id)
            .order_by(Application.updated_at.desc().nullslast(), Application.id.desc())
            .all())


@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application(application_id: int, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    return _get_owned(db, application_id, current_user)


@router.put("/{application_id}", response_model=ApplicationResponse)
def update_application(application_id: int, updates: ApplicationUpdate, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    application = _get_owned(db, application_id, current_user)

    # exclude_unset=True → only the fields the client actually sent
    update_data = updates.model_dump(exclude_unset=True)
    old_status = application.status
    if update_data.get("track_email") and not application.track_email:
        application.track_email_since = utcnow()     # newly tracked → full look-back next sync
    for field, value in update_data.items():
        setattr(application, field, value)

    # First time it leaves "Saved" = the day they really applied.
    # Email search for this application starts from this date.
    if old_status == "Saved" and application.status != "Saved" and application.applied_at is None:
        application.applied_at = utcnow()

    db.commit()
    db.refresh(application)
    return application


@router.delete("/{application_id}")
def delete_application(application_id: int, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    application = _get_owned(db, application_id, current_user)
    # ORM cascade deletes its email events + notifications too
    db.delete(application)
    db.commit()
    return {"message": "Application deleted successfully"}
