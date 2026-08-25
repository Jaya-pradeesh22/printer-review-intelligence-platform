from sqlalchemy import Column, Integer, String  # type: ignore[import]
from app.database.database import Base

class IssueCategory(Base):
    __tablename__ = "issue_categories"
    id = Column(Integer, primary_key=True, index=True)
    category_name = Column(String, nullable=False)
    