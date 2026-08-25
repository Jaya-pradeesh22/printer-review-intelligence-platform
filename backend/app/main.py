from app.models.review import Review
from app.schemas.review_schema import ReviewCreate
from app.models.issue_category import IssueCategory
from app.models.issue_category import IssueCategory
from app.services.sentiment_analyzer import detect_sentiment
from app.models.review_issue_mapping import ReviewIssueMapping
from app.services.issue_classifier import detect_issue_categories
from app.models.review_issue_mapping import ReviewIssueMapping
from fastapi import FastAPI
from sqlalchemy.orm import Session

from sqlalchemy import func

from app.database.database import engine, Base, SessionLocal
from app.models.product import Product
from app.schemas.product_schemas import ProductCreate

from app.api.review_api import router as review_router

from app.api.analytics_api import router as analytics_router

Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/test")
def test():
    return {"message": "working"}

app.include_router(
    review_router,
    tags=["Reviews"]
)

app.include_router(
    analytics_router,
    tags=["Analytics"]
)

@app.get("/")
def home():
    return {"message": "Printer Review Intelligence Platform API"}

@app.post("/products/")
def create_product(product: ProductCreate):

    db: Session = SessionLocal()

    new_product = Product(product_name=product.product_name, printer_type=product.printer_type, model_name=product.model_name)
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    db.close()

    return{
        "message": "Product created successfully",
        "product": new_product.product_name
    }

@app.get("/produts")
def get_products():
    db: Session = SessionLocal()
    products = db.query(Product).all()
    db.close()
    return products

@app.post("/reviews")
def create_review(review: ReviewCreate):
    db: Session = SessionLocal()
    sentiment = detect_sentiment(review.review_text)

    # Create review object
    new_review = Review(
        product_id=review.product_id,
        review_text=review.review_text,
        rating=review.rating,
        source=review.source,
        sentiment=sentiment
    )

    db.add(new_review)
    db.commit()
    
    db.refresh(new_review)
    detected_categories = detect_issue_categories(review.review_text)

    for category_name in detected_categories:
        category = db.query(IssueCategory).filter(
            IssueCategory.category_name == category_name
        ).first()

        if category:
            mapping = ReviewIssueMapping(
                review_id=new_review.id,
                issue_category_id = category.id
            )
            db.add(mapping)
    db.commit()
    
    db.close()
    return{
        "message": "Review created successfully"
    }

@app.get("/analytics/issue-sentiment")
def issue_sentiment_analytics():
    db: Session = SessionLocal()

    results = db.query(
        IssueCategory.category_name,
        Review.sentiment,
        func.count(Review.id)

    ).join(
        ReviewIssueMapping,
        IssueCategory.id == ReviewIssueMapping.issue_category_id
    ).join(
        Review,
        Review.id == ReviewIssueMapping.review_id
    ).group_by(
        IssueCategory.category_name,
        Review.sentiment
    ).all()

    db.close()
    analytics={}
    for category, sentiment, count in results:
        if category not in analytics:
            analytics[category] = {
                "category":category,
                "POSITIVE":0,
                "NEGATIVE":0,
                "NEUTRAL":0
            }

        analytics[category][sentiment]=count
    return list(analytics.values())

# @app.get("/analytics/reviews")
# def model_issue_analytics():

#     db: Session = SessionLocal()

#     results = db.query(
#         Product.model_name,
#         IssueCategory.category_name,
#         Review.sentiment,
#         func.count(Review.id)
#     ).join(
#         Review,
#         Product.id == Review.product_id
#     ).join(
#         ReviewIssueMapping,
#         Review.id == ReviewIssueMapping.review_id
#     ).join(
#         IssueCategory,
#         IssueCategory.id == ReviewIssueMapping.issue_category_id
#     ).group_by(
#         Product.model_name,
#         IssueCategory.category_name,
#         Review.sentiment
#     ).all()

#     db.close()

#     analytics = []

#     for model_name, category, sentiment, count in results:

#         analytics.append({
#             "model_name": model_name,
#             "category": category,
#             "sentiment": sentiment,
#             "count": count
#         })

#     return analytics

@app.get("/analytics/reviews")
def get_review_details():

    db: Session = SessionLocal()

    reviews = db.query(
        Review.id,
        Product.model_name,
        Review.review_text,
        Review.rating,
        Review.source,
        Review.sentiment
    ).join(
        Product,
        Product.id == Review.product_id
    ).all()

    result = []

    for review in reviews:

        issues = db.query(
            IssueCategory.category_name
        ).join(
            ReviewIssueMapping,
            IssueCategory.id ==
            ReviewIssueMapping.issue_category_id
        ).filter(
            ReviewIssueMapping.review_id ==
            review.id
        ).all()

        issue_list = [
            issue.category_name
            for issue in issues
        ]

        result.append({
            "model_name": review.model_name,
            "review": review.review_text,
            "rating": review.rating,
            "source": review.source,
            "sentiment": review.sentiment,
            "issues": issue_list
        })

    db.close()

    return result