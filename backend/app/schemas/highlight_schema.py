from pydantic import BaseModel
from typing import Optional


class HighlightCreate(BaseModel):
    model_name: str
    category: str
    mention_count: int
    trend: str
    source: Optional[str] = "Amazon"