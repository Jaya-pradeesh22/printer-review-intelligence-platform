from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.database.database import Base


class AuditLog(Base):
    """
    Records every admin edit / delete / bulk re-classify made from the
    dashboard's "Manage / Edit Reviews" panel, for accountability.
    """

    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    actor = Column(String, nullable=False)           # dashboard username, e.g. "admin"
    action = Column(String, nullable=False, index=True)  # "edit" | "delete" | "bulk_reclassify"
    review_id = Column(Integer, nullable=True)        # RawReview.id (nullable for bulk ops)
    details = Column(Text, nullable=True)             # human-readable summary of what changed
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
