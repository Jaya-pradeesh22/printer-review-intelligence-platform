from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.models.raw_review import RawReview
from app.schemas.raw_review_schema import RawReviewCreate

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/raw-reviews")
def create_reviews(reviews: List[RawReviewCreate], db: Session = Depends(get_db)):
    """
    Batch insert, deduped on (source, review_id). Safe to re-run the same
    scrape run repeatedly - already-stored reviews are skipped, not duplicated.
    """
    existing_keys = {
        (row.source, row.review_id)
        for row in db.query(RawReview.source, RawReview.review_id)
        .filter(
            RawReview.source.in_({r.source for r in reviews}),
            RawReview.review_id.in_([r.review_id for r in reviews]),
        )
        .all()
    }

    new_rows = [r for r in reviews if (r.source, r.review_id) not in existing_keys]

    for r in new_rows:
        db.add(RawReview(**r.dict()))

    db.commit()

    return {
        "message": "Reviews processed",
        "received": len(reviews),
        "inserted": len(new_rows),
        "skipped_duplicates": len(reviews) - len(new_rows),
    }


@router.get("/raw-reviews")
def get_reviews(
    model_name: Optional[str] = None,
    source: Optional[str] = None,
    sentiment: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Powers the KPI drill-down tables - filter by sentiment (Positive/Negative/
    Neutral card click) or by model_name/source/category as needed.
    """
    query = db.query(RawReview)
    if model_name:
        query = query.filter(RawReview.model_name == model_name)
    if source:
        query = query.filter(RawReview.source == source)
    if sentiment:
        query = query.filter(RawReview.sentiment == sentiment.upper())
    if category:
        query = query.filter(RawReview.category == category)

    return query.order_by(RawReview.scraped_at.desc()).all()


@router.get("/raw-reviews/summary")
def get_reviews_summary(db: Session = Depends(get_db)):
    """
    Powers the four home-page KPI cards: total / positive / negative / neutral,
    broken down per model_name so the drill-down table can group by printer.
    """
    rows = (
        db.query(
            RawReview.model_name,
            RawReview.sentiment,
            func.count(RawReview.id).label("count"),
        )
        .group_by(RawReview.model_name, RawReview.sentiment)
        .all()
    )

    summary = {}
    for model_name, sentiment, count in rows:
        entry = summary.setdefault(
            model_name, {"total": 0, "positive": 0, "negative": 0, "neutral": 0}
        )
        entry["total"] += count
        key = (sentiment or "neutral").lower()
        if key in entry:
            entry[key] += count

    return summary