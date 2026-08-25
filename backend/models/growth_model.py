import secrets
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base


def yeni_kimlik() -> str:
    return str(uuid.uuid4())


new_id = yeni_kimlik


class LearningProgress(Base):
    __tablename__ = "learning_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "lesson_key", name="uq_learning_user_lesson"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=yeni_kimlik)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    lesson_key: Mapped[str] = mapped_column(String(80), nullable=False)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )


class LearningAttempt(Base):
    __tablename__ = "learning_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=yeni_kimlik)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    lesson_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    answer_index: Mapped[int] = mapped_column(Integer, nullable=False)
    correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )


class EmailCampaign(Base):
    __tablename__ = "email_campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=yeni_kimlik)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    reply_to: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )
    recipients: Mapped[list["EmailRecipient"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )


class EmailRecipient(Base):
    __tablename__ = "email_recipients"
    __table_args__ = (
        UniqueConstraint("campaign_id", "email", name="uq_campaign_email"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=yeni_kimlik)
    campaign_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("email_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(160))
    company_name: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    error_message: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    unsubscribe_token: Mapped[str | None] = mapped_column(
        String(64), unique=True, default=lambda: secrets.token_urlsafe(32)
    )
    unsubscribed_at: Mapped[datetime | None] = mapped_column(DateTime)
    tracking_token: Mapped[str | None] = mapped_column(
        String(64), unique=True, default=lambda: secrets.token_urlsafe(32)
    )
    opened_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_opened_at: Mapped[datetime | None] = mapped_column(DateTime)
    open_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    message_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime)
    reply_subject: Mapped[str | None] = mapped_column(String(500))
    reply_from: Mapped[str | None] = mapped_column(String(255))
    delivery_status: Mapped[str | None] = mapped_column(String(30))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime)
    bounced_at: Mapped[datetime | None] = mapped_column(DateTime)
    complained_at: Mapped[datetime | None] = mapped_column(DateTime)
    bounce_reason: Mapped[str | None] = mapped_column(String(500))
    campaign: Mapped[EmailCampaign] = relationship(back_populates="recipients")


class EmailDeliveryEvent(Base):
    __tablename__ = "email_delivery_events"
    __table_args__ = (
        UniqueConstraint("provider", "event_id", name="uq_email_delivery_event"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=yeni_kimlik)
    recipient_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("email_recipients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )


class DemandPost(Base):
    __tablename__ = "demand_posts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=yeni_kimlik)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("products_v2.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[str | None] = mapped_column(String(100))
    target_country: Mapped[str] = mapped_column(String(100), nullable=False)
    deadline: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )
    targets: Mapped[list["DemandPostTarget"]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )


class DemandPostTarget(Base):
    __tablename__ = "demand_post_targets"
    __table_args__ = (
        UniqueConstraint("demand_post_id", "platform", name="uq_demand_platform"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=yeni_kimlik)
    demand_post_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("demand_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    publication_url: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    post: Mapped[DemandPost] = relationship(back_populates="targets")


class AdminAction(Base):
    __tablename__ = "admin_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=yeni_kimlik)
    actor_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    target_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )


class TradeMarketSnapshot(Base):
    __tablename__ = "trade_market_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "product_id",
            "target_country",
            "period",
            "hs_code",
            name="uq_trade_market_snapshot",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=yeni_kimlik)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("products_v2.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_country: Mapped[str] = mapped_column(String(100), nullable=False)
    reporter_code: Mapped[str] = mapped_column(String(20), nullable=False)
    reporter_name: Mapped[str | None] = mapped_column(String(160))
    hs_code: Mapped[str] = mapped_column(String(10), nullable=False)
    commodity: Mapped[str | None] = mapped_column(Text)
    period: Mapped[int] = mapped_column(Integer, nullable=False)
    import_value_usd: Mapped[float] = mapped_column(Float, nullable=False)
    net_weight_kg: Mapped[float | None] = mapped_column(Float)
    quantity: Mapped[float | None] = mapped_column(Float)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )


EgitimIlerlemesi = LearningProgress
EgitimDenemesi = LearningAttempt
EpostaKampanyasi = EmailCampaign
EpostaAlicisi = EmailRecipient
EpostaIletimOlayi = EmailDeliveryEvent
TalepIlani = DemandPost
TalepIlaniHedefi = DemandPostTarget
YoneticiIslemi = AdminAction
TicaretPiyasaVerisi = TradeMarketSnapshot
