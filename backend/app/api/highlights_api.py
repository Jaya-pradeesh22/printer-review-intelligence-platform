from fastapi import APIRouter
from sqlalchemy.orm import Session
from typing import List

from app.database.database import SessionLocal
from app.models.product_highlight import ProductHighlight
from app.schemas.highlight_schema import HighlightCreate

router = APIRouter()


@router.post("/highlights")
def create_highlights(highlights: List[HighlightCreate]):
    """
    Bulk insert - the scraper POSTs its full list of scraped
    highlights here in one call after each run.
    """
    db: Session = SessionLocal()

    saved_count = 0

    for item in highlights:
        new_highlight = ProductHighlight(
            model_name=item.model_name,
            category=item.category,
            mention_count=item.mention_count,
            trend=item.trend,
            source=item.source
        )
        db.add(new_highlight)
        saved_count += 1

    db.commit()
    db.close()

    return {
        "message": "Highlights saved successfully",
        "count": saved_count
    }


@router.get("/highlights")
def get_highlights():
    """
    Returns the most recent scrape per (model_name, category) pair,
    so re-running the scraper doesn't pile up stale duplicates in
    the dashboard.
    """
    db: Session = SessionLocal()

    all_rows = db.query(ProductHighlight).order_by(
        ProductHighlight.scraped_at.desc()
    ).all()

    db.close()

    latest = {}
    for row in all_rows:
        key = (row.model_name, row.category)
        if key not in latest:
            latest[key] = {
                "model_name": row.model_name,
                "category": row.category,
                "mention_count": row.mention_count,
                "trend": row.trend,
                "source": row.source,
                "scraped_at": row.scraped_at.isoformat()
                if row.scraped_at else None
            }

    return list(latest.values())