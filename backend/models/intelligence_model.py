import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from core.database import Base


def _yeni_kimlik() -> str:
    return str(uuid.uuid4())


_id = _yeni_kimlik


class RFQSearch(Base):
    __tablename__ = "rfq_searches"

    id = Column(String(36), primary_key=True, default=_yeni_kimlik)
    user_id = Column(String(36), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products_v2.id", ondelete="CASCADE"), nullable=False)
    target_country = Column(String(100), default="Türkiye")
    date_from = Column(DateTime, nullable=True)
    status = Column(String(40), default="PENDING", nullable=False)
    progress = Column(Integer, default=0, nullable=False)
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    opportunities = relationship("RFQOpportunity", cascade="all, delete-orphan", back_populates="search")


class RFQOpportunity(Base):
    __tablename__ = "rfq_opportunities"
    __table_args__ = (UniqueConstraint("rfq_search_id", "source_url", name="uq_rfq_source"),)

    id = Column(String(36), primary_key=True, default=_yeni_kimlik)
    rfq_search_id = Column(String(36), ForeignKey("rfq_searches.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    buyer_name = Column(String(255), nullable=True)
    country = Column(String(100), nullable=True)
    quantity = Column(String(100), nullable=True)
    deadline = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    platform = Column(String(100), nullable=True)
    source_url = Column(Text, nullable=False)
    source_type = Column(String(50), default="indexed_public")
    access_status = Column(String(30), default="public", nullable=False)
    relevance_score = Column(Integer, default=0, nullable=False)
    freshness_score = Column(Integer, default=50, nullable=False)
    confidence_score = Column(Integer, default=0, nullable=False)
    match_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    search = relationship("RFQSearch", back_populates="opportunities")


class ContactDiscovery(Base):
    __tablename__ = "contact_discoveries"

    id = Column(String(36), primary_key=True, default=_yeni_kimlik)
    user_id = Column(String(36), nullable=False, index=True)
    company_id = Column(String(36), ForeignKey("crawler_companies.id", ondelete="SET NULL"), nullable=True)
    company_name = Column(String(255), nullable=False)
    domain = Column(String(255), nullable=True)
    status = Column(String(40), default="PENDING", nullable=False)
    progress = Column(Integer, default=0, nullable=False)
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    contacts = relationship("CompanyContact", cascade="all, delete-orphan", back_populates="discovery")


class CompanyContact(Base):
    __tablename__ = "company_contacts"
    __table_args__ = (UniqueConstraint("contact_discovery_id", "source_url", "full_name", name="uq_contact_source_name"),)

    id = Column(String(36), primary_key=True, default=_yeni_kimlik)
    contact_discovery_id = Column(String(36), ForeignKey("contact_discoveries.id", ondelete="CASCADE"), nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    role = Column(String(255), nullable=True)
    company_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(100), nullable=True)
    source_url = Column(Text, nullable=False)
    source_type = Column(String(50), default="indexed_public")
    access_status = Column(String(30), default="public", nullable=False)
    confidence_score = Column(Integer, default=0, nullable=False)
    match_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    discovery = relationship("ContactDiscovery", back_populates="contacts")


class FairAnalysis(Base):
    __tablename__ = "fair_analyses"

    id = Column(String(36), primary_key=True, default=_yeni_kimlik)
    user_id = Column(String(36), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products_v2.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    source_columns = Column(JSON, default=list, nullable=False)
    column_mapping = Column(JSON, default=dict, nullable=False)
    total_rows = Column(Integer, default=0, nullable=False)
    processed_rows = Column(Integer, default=0, nullable=False)
    duplicate_rows = Column(Integer, default=0, nullable=False)
    status = Column(String(40), default="UPLOADED", nullable=False)
    progress = Column(Integer, default=0, nullable=False)
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    entries = relationship("FairEntry", cascade="all, delete-orphan", back_populates="analysis")


class FairEntry(Base):
    __tablename__ = "fair_entries"

    id = Column(String(36), primary_key=True, default=_yeni_kimlik)
    fair_analysis_id = Column(String(36), ForeignKey("fair_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    row_number = Column(Integer, nullable=False)
    company_name = Column(String(255), nullable=False)
    website = Column(Text, nullable=True)
    country = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    sector = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(100), nullable=True)
    access_status = Column(String(30), default="public", nullable=False)
    relevance_score = Column(Integer, default=0, nullable=False)
    buyer_score = Column(Integer, default=0, nullable=False)
    classification = Column(String(40), nullable=False)
    matched_terms = Column(JSON, default=list, nullable=False)
    match_reason = Column(Text, nullable=True)
    original_data = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    analysis = relationship("FairAnalysis", back_populates="entries")


class AssistantConversation(Base):
    __tablename__ = "assistant_conversations"

    id = Column(String(36), primary_key=True, default=_yeni_kimlik)
    user_id = Column(String(36), nullable=False, index=True)
    title = Column(String(255), default="Pusula Asistanı")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    messages = relationship("AssistantMessage", cascade="all, delete-orphan", back_populates="conversation")


class AssistantMessage(Base):
    __tablename__ = "assistant_messages"

    id = Column(String(36), primary_key=True, default=_yeni_kimlik)
    conversation_id = Column(String(36), ForeignKey("assistant_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    mode = Column(String(20), default="fallback", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    conversation = relationship("AssistantConversation", back_populates="messages")


AlimTalebiAramasi = RFQSearch
AlimTalebiFirsati = RFQOpportunity
YetkiliKesfi = ContactDiscovery
FirmaYetkilisi = CompanyContact
FuarAnalizi = FairAnalysis
FuarKatilimcisi = FairEntry
AsistanSohbeti = AssistantConversation
AsistanMesaji = AssistantMessage
