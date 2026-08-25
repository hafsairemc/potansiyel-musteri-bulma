import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base


def yeni_kimlik() -> str:
    return str(uuid.uuid4())


new_id = yeni_kimlik


class ProductModel(Base):
    __tablename__ = "products_v2"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=yeni_kimlik, index=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    oem: Mapped[str | None] = mapped_column(String(100), index=True)
    hs_code: Mapped[str | None] = mapped_column(String(50), index=True)
    name_tr: Mapped[str] = mapped_column(Text, nullable=False)
    name_en: Mapped[str | None] = mapped_column(Text)
    name_de: Mapped[str | None] = mapped_column(Text)
    name_fr: Mapped[str | None] = mapped_column(Text)
    name_ru: Mapped[str | None] = mapped_column(Text)
    name_es: Mapped[str | None] = mapped_column(Text)
    name_ar: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    search_profile: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=True)
    target_languages: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=True
    )

    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", lazy="selectin"
    )
    competitors: Mapped[list["ProductCompetitor"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", lazy="selectin"
    )
    industries: Mapped[list["ProductIndustry"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", lazy="selectin"
    )
    target_countries: Mapped[list["ProductTargetCountry"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", lazy="selectin"
    )


class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=yeni_kimlik, index=True)
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products_v2.id", ondelete="CASCADE"), nullable=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    product: Mapped[ProductModel] = relationship(back_populates="images")


class ProductCompetitor(Base):
    __tablename__ = "product_competitors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=yeni_kimlik, index=True)
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products_v2.id", ondelete="CASCADE"), nullable=True
    )
    brand_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product: Mapped[ProductModel] = relationship(back_populates="competitors")


class ProductIndustry(Base):
    __tablename__ = "product_industries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=yeni_kimlik, index=True)
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products_v2.id", ondelete="CASCADE"), nullable=True
    )
    industry_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product: Mapped[ProductModel] = relationship(back_populates="industries")


class ProductTargetCountry(Base):
    __tablename__ = "product_target_countries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=yeni_kimlik, index=True)
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products_v2.id", ondelete="CASCADE"), nullable=True
    )
    country_name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain_extension: Mapped[str | None] = mapped_column(String(50))
    product: Mapped[ProductModel] = relationship(back_populates="target_countries")


UrunModeli = ProductModel
UrunResmi = ProductImage
UrunRakibi = ProductCompetitor
UrunSektoru = ProductIndustry
UrunHedefUlke = ProductTargetCountry
