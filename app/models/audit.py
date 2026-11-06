
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String
from app.database import Base


class Audit(Base):
    __tablename__ = "audits"

    id = Column(Integer, primary_key=True, index=True)
    website_url = Column(String(500), nullable=False)
    status = Column(String(50), default="pending")
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
