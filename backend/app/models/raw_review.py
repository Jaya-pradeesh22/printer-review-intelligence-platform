from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint
from sqlalchemy.sql import func

from app.database.database import Base


class RawReview(Base):
    """
    Unified raw review storage for all sources (Amazon, HP.com, future sources).
    review_id is only guaranteed unique WITHIN a source (Amazon and HP could both
    theoretically produce the same review_id string), so the uniqueness constraint
    is on (source, review_id) together, not review_id alone.
    """

    __tablename__ = "raw_reviews"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False, index=True)          # "Amazon" | "HP.com"
    review_id = Column(String, nullable=False, index=True)
    model_name = Column(String, nullable=False, index=True)
    rating_value = Column(Integer, nullable=True)
    review_body = Column(Text, nullable=False)
    reviewer_response = Column(Text, nullable=True)               # seller/brand reply, if any

    category = Column(String, nullable=True, index=True)          # from ai_classifier.py
    sentiment = Column(String, nullable=True, index=True)         # POSITIVE | NEGATIVE | NEUTRAL
    sentiment_source = Column(String, nullable=True)              # "rating_heuristic" | "ollama"

    scraped_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("source", "review_id", name="uq_source_review_id"),
    )
