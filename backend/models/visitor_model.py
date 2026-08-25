import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from core.database import Base


class VisitorModel(Base):
    __tablename__ = "visitors"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    permission = Column(String(50), nullable=True)
    country = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    formatted_address = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    ip = Column(String(100), nullable=True)
    operator = Column(String(255), nullable=True)
    detection_method = Column(String(50), nullable=True)
    confidence = Column(Float, nullable=True)
    retention_until = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.now)


class VisitorNotification(Base):
    __tablename__ = "visitor_notifications"
    __table_args__ = (
        UniqueConstraint("visitor_id", "user_id", name="uq_visitor_notification_owner"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    visitor_id = Column(
        String(36),
        ForeignKey("visitors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(String(36), nullable=False, index=True)
    read_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


ZiyaretciModeli = VisitorModel
ZiyaretciBildirimi = VisitorNotification
