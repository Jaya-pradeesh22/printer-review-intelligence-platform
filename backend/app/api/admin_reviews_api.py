"""
Admin-only endpoints for the "Manage / Edit Reviews" panel in dashboard.py.

Place this file at: app/api/admin_reviews_api.py

Then in main.py add:

    from app.models.audit_log import AuditLog
    from app.api.admin_reviews_api import router as admin_reviews_router
    app.include_router(admin_reviews_router, tags=["Admin"])

Importing AuditLog before Base.metadata.create_all(bind=engine) is what
gets the audit_log table created — main.py already imports every other
model the same way (e.g. `from app.models.raw_review import RawReview`),
so just add the AuditLog import alongside those.

ASSUMPTION: classify_review(review_text, rating) lives at
app/services/ai_classifier.py per your existing pipeline scripts. Adjust
the import below if it's actually somewhere else.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.database.database import SessionLocal
from app.models.raw_review import RawReview
from app.models.audit_log import AuditLog
from app.services.ai_classifier import classify_review  # <-- adjust path if different

router = APIRouter()


class ReviewUpdate(BaseModel):
    category: Optional[str] = None
    sentiment_source: Optional[str] = None
    actor: str


class BulkReclassifyRequest(BaseModel):
    review_ids: List[int]
    actor: str


def _log_action(db, actor, action, review_id, details):
    entry = AuditLog(actor=actor, action=action, review_id=review_id, details=details)
    db.add(entry)
    db.commit()


@router.patch("/raw-reviews/{review_id}")
def edit_review(review_id: int, payload: ReviewUpdate):
    db = SessionLocal()
    review = db.query(RawReview).filter(RawReview.id == review_id).first()
    if not review:
        db.close()
        raise HTTPException(status_code=404, detail="Review not found")

    changes = []
    if payload.category is not None and payload.category != review.category:
        changes.append(f"category: '{review.category}' -> '{payload.category}'")
        review.category = payload.category
    if payload.sentiment_source is not None and payload.sentiment_source != review.sentiment_source:
        changes.append(f"sentiment: '{review.sentiment_source}' -> '{payload.sentiment_source}'")
        review.sentiment_source = payload.sentiment_source
        # keep the display-facing sentiment column in sync too
        review.sentiment = payload.sentiment_source

    if not changes:
        db.close()
        return {"status": "no changes"}

    db.commit()
    _log_action(db, payload.actor, "edit", review_id, "; ".join(changes))
    db.close()
    return {"status": "updated", "id": review_id}


@router.delete("/raw-reviews/{review_id}")
def delete_review(review_id: int, actor: str):
    db = SessionLocal()
    review = db.query(RawReview).filter(RawReview.id == review_id).first()
    if not review:
        db.close()
        raise HTTPException(status_code=404, detail="Review not found")

    summary = f"deleted review from {review.source} (model: {review.model_name})"
    db.delete(review)
    db.commit()
    _log_action(db, actor, "delete", review_id, summary)
    db.close()
    return {"status": "deleted", "id": review_id}


@router.post("/raw-reviews/bulk-reclassify")
def bulk_reclassify(payload: BulkReclassifyRequest):
    db = SessionLocal()
    reviews = db.query(RawReview).filter(RawReview.id.in_(payload.review_ids)).all()
    if not reviews:
        db.close()
        raise HTTPException(status_code=404, detail="No matching reviews found")

    updated = 0
    for review in reviews:
           old_category, old_sentiment = review.category, review.sentiment_source
           result = classify_review(review.review_body, review.rating_value)
           new_category, new_sentiment = result["category"], result["sentiment"]
           if new_category != old_category or new_sentiment != old_sentiment:
               review.category = new_category
               review.sentiment_source = result["sentiment_source"]
               review.sentiment = new_sentiment
               updated += 1

    db.commit()
    _log_action(
        db, payload.actor, "bulk_reclassify", None,
        f"re-classified {len(reviews)} review(s), {updated} changed"
    )
    db.close()
    return {"status": "done", "processed": len(reviews), "updated": updated}


@router.get("/audit-log")
def get_audit_log(limit: int = 50):
    db = SessionLocal()
    entries = (
        db.query(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
        .all()
    )
    db.close()
    return [
        {
            "id": e.id,
            "actor": e.actor,
            "action": e.action,
            "review_id": e.review_id,
            "details": e.details,
            "timestamp": e.timestamp,
        }
        for e in entries
    ]
