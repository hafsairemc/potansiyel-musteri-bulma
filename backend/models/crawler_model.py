import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.product_model import ProductModel


def yeni_kimlik() -> str:
    return str(uuid.uuid4())


new_id = yeni_kimlik

crawler_company_products = Table(
    "crawler_company_products",
    Base.metadata,
    Column("company_id", String(36), ForeignKey("crawler_companies.id", ondelete="CASCADE"), primary_key=True),
    Column("product_id", String(36), ForeignKey("crawler_products.id", ondelete="CASCADE"), primary_key=True),
)


class SearchBatch(Base):
    __tablename__ = "search_batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=yeni_kimlik, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products_v2.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False, index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_jobs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_jobs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_jobs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    jobs: Mapped[list["CrawlerSearchJob"]] = relationship(back_populates="batch", cascade="all, delete-orphan")
    exports: Mapped[list["SearchExport"]] = relationship(back_populates="batch", cascade="all, delete-orphan")


class CrawlerSearchJob(Base):
    __tablename__ = "crawler_search_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=yeni_kimlik, index=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    product_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("products_v2.id", ondelete="CASCADE"))
    batch_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("search_batches.id", ondelete="CASCADE"), index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime)
    target_country: Mapped[str | None] = mapped_column(String(100))
    search_query: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    search_engine: Mapped[str] = mapped_column(String(100), default="Google", nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="search_engine", nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    report_url: Mapped[str | None] = mapped_column(String(500))
    total_companies: Mapped[int] = mapped_column(Integer, default=0, nullable=True)
    successful_companies: Mapped[int] = mapped_column(Integer, default=0, nullable=True)
    failed_companies: Mapped[int] = mapped_column(Integer, default=0, nullable=True)
    robots_allowed: Mapped[int] = mapped_column(Integer, default=0, nullable=True)
    robots_blocked: Mapped[int] = mapped_column(Integer, default=0, nullable=True)
    robots_unknown: Mapped[int] = mapped_column(Integer, default=0, nullable=True)
    force_crawl: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    crawler_logs: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)

    results: Mapped[list["CrawlerSearchResult"]] = relationship(back_populates="search_job", cascade="all, delete-orphan")
    metrics: Mapped["CrawlerSearchJobMetrics | None"] = relationship(back_populates="search_job", uselist=False, cascade="all, delete-orphan")
    batch: Mapped[SearchBatch | None] = relationship(back_populates="jobs")
    product: Mapped[ProductModel | None] = relationship()


class CrawlerSearchJobMetrics(Base):
    __tablename__ = "crawler_search_job_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=yeni_kimlik, index=True)
    search_job_id: Mapped[str] = mapped_column(String(36), ForeignKey("crawler_search_jobs.id", ondelete="CASCADE"), unique=True, nullable=False)
    timeout_count: Mapped[int] = mapped_column(Integer, default=0, nullable=True)
    captcha_count: Mapped[int] = mapped_column(Integer, default=0, nullable=True)
    total_runtime_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=True)
    avg_response_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=True)
    search_job: Mapped[CrawlerSearchJob] = relationship(back_populates="metrics")


class CrawlerCompany(Base):
    __tablename__ = "crawler_companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=yeni_kimlik, index=True)
    name: Mapped[str | None] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    email_status: Mapped[str | None] = mapped_column(String(30))
    email_source_url: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(String(100), index=True)
    city: Mapped[str | None] = mapped_column(String(100), index=True)
    about_us_text: Mapped[str | None] = mapped_column(Text)
    contact_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=True)

    websites: Mapped[list["CrawlerCompanyWebsite"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    search_results: Mapped[list["CrawlerSearchResult"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    products: Mapped[list["CrawlerProduct"]] = relationship(secondary=crawler_company_products, back_populates="companies")


class CrawlerCompanyWebsite(Base):
    __tablename__ = "crawler_company_websites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=yeni_kimlik, index=True)
    company_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("crawler_companies.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), index=True, nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=True)
    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime)
    company: Mapped[CrawlerCompany | None] = relationship(back_populates="websites")


class CrawlerSearchResult(Base):
    __tablename__ = "crawler_search_results"
    __table_args__ = (UniqueConstraint("search_job_id", "source_url", name="uq_job_source_url"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=yeni_kimlik, index=True)
    search_job_id: Mapped[str] = mapped_column(String(36), ForeignKey("crawler_search_jobs.id", ondelete="CASCADE"), nullable=False)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("crawler_companies.id", ondelete="CASCADE"), nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    position: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(50), default="search_engine", nullable=False)
    platform: Mapped[str | None] = mapped_column(String(100))
    search_query: Mapped[str | None] = mapped_column(Text)
    sector_match: Mapped[str] = mapped_column(String(20), default="main", nullable=False)
    customer_type: Mapped[str | None] = mapped_column(String(50))
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    confidence_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    relevance_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    buyer_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matched_terms: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    category_path: Mapped[str | None] = mapped_column(String(500))
    match_reason: Mapped[str | None] = mapped_column(Text)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=True)

    search_job: Mapped[CrawlerSearchJob] = relationship(back_populates="results")
    company: Mapped[CrawlerCompany] = relationship(back_populates="search_results")


class SearchExport(Base):
    __tablename__ = "search_exports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=yeni_kimlik, index=True)
    batch_id: Mapped[str] = mapped_column(String(36), ForeignKey("search_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)
    file_url: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    filters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    batch: Mapped[SearchBatch] = relationship(back_populates="exports")


class CrawlerProduct(Base):
    __tablename__ = "crawler_products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=yeni_kimlik, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False, unique=True)
    companies: Mapped[list[CrawlerCompany]] = relationship(secondary=crawler_company_products, back_populates="products")


AramaPaketi = SearchBatch
AramaGorevi = CrawlerSearchJob
AramaMetrikleri = CrawlerSearchJobMetrics
BulunanFirma = CrawlerCompany
FirmaWebSitesi = CrawlerCompanyWebsite
AramaSonucuKaydi = CrawlerSearchResult
AramaDisaAktarma = SearchExport
TarananUrun = CrawlerProduct
