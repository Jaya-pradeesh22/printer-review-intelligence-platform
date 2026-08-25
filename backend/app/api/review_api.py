from fastapi import APIRouter
from app.services.review_service import(
    get_analyzed_reviews,
    get_reviews
)

router = APIRouter()

@router.get("/reviews")
def fetch_reviews():
    return get_reviews()

@router.get("/reviews/analyze")
def analyze_reviews():
    return get_analyzed_reviews()