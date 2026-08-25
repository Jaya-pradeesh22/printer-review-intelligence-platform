from sqlalchemy import Column, Integer, String, Text, ForeignKey
from app.database.database import Base

class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    review_text = Column(Text, nullable=False)
    rating = Column(Integer)
    source = Column(String)
    sentiment = Column(String)

