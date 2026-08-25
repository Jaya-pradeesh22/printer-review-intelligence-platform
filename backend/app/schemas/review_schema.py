from pydantic import BaseModel

class ReviewCreate(BaseModel):

    product_id: int
    review_text: str
    rating: int
    source: str