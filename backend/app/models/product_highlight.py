from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.database.database import Base


class ProductHighlight(Base):
    __tablename__ = "product_highlights"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    mention_count = Column(Integer, nullable=False)
    trend = Column(String, nullable=False)
    source = Column(String, nullable=True)
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())