from pydantic import BaseModel
from typing import Optional


class RawReviewCreate(BaseModel):
    source: str
    review_id: str
    model_name: str
    rating_value: Optional[int] = None
    review_body: str
    reviewer_response: Optional[str] = None
    category: Optional[str] = None
    sentiment: Optional[str] = None
    sentiment_source: Optional[str] = "rating_heuristic"
