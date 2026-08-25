from sqlalchemy import Column, Integer, ForeignKey
from app.database.database import Base

class ReviewIssueMapping(Base):
    __tablename__ = "review_issue_mapping"
    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("reviews.id"))
    issue_category_id = Column(Integer, ForeignKey("issue_categories.id"))
