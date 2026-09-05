from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.services.insight_generator import generate_insights
from app.database.database import SessionLocal
from app.models.product_highlight import ProductHighlight

router = APIRouter()


class HighlightItem(BaseModel):
    model_name: str
    category: str
    mention_count: int
    trend: str


class InsightRequest(BaseModel):
    highlights: list[HighlightItem]


@router.post("/insights")
def get_insights(request: InsightRequest):
    highlights_data = [item.dict() for item in request.highlights]
    report = generate_insights(highlights_data)

    return {
        "insights": report
    }


@router.get("/insights/latest")
def get_insights_from_db():
    """
    Generates the QA report straight from the latest scraped data
    already stored in the database - no manual copy-paste needed.
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
                "trend": row.trend
            }

    report = generate_insights(list(latest.values()))

    return {
        "insights": report
    }