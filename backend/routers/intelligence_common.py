from collections.abc import Callable
from typing import Any
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.product_model import ProductModel


async def kullanici_kaydini_al(
    db: AsyncSession,
    model: Any,
    record_id: str,
    user_id: str,
):
    sorgu = select(model).where(model.id == record_id, model.user_id == user_id)
    kayit = (await db.execute(sorgu)).scalar_one_or_none()
    if kayit is None:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı")
    return kayit


async def kaydi_kuyruga_ekle(
    db: AsyncSession,
    record: Any,
    kuyruga_ekle: Callable[[str], None],
) -> None:
    record.status = "QUEUED"
    await db.commit()
    try:
        kuyruga_ekle(record.id)
    except Exception as exc:
        record.status = "FAILED"
        record.error_code = "QUEUE_UNAVAILABLE"
        record.error_message = str(exc)[:1500]
        await db.commit()
        raise HTTPException(status_code=503, detail="Görev kuyruğuna ulaşılamadı") from exc


async def urun_bul_veya_olustur(
    db: AsyncSession,
    user_id: str,
    product_input: str,
    default_hs: str | None = None,
) -> ProductModel:
    deger = (product_input or "").strip()
    if not deger:
        raise HTTPException(422, "Ürün adı veya kodu gereklidir")

    sorgu_id = select(ProductModel).where(ProductModel.id == deger, ProductModel.user_id == user_id)
    urun = (await db.execute(sorgu_id)).scalar_one_or_none()
    if urun:
        return urun

    sorgu_isim = select(ProductModel).where(func.lower(ProductModel.name_tr) == deger.lower(), ProductModel.user_id == user_id)
    urun = (await db.execute(sorgu_isim)).scalar_one_or_none()
    if urun:
        return urun

    rakamsal_mi = deger.replace(".", "").replace(" ", "").isdigit() and len(deger.replace(".", "").replace(" ", "")) >= 4
    urun = ProductModel(
        user_id=user_id,
        name_tr=deger,
        hs_code=default_hs or (deger if rakamsal_mi else None),
    )
    db.add(urun)
    await db.commit()
    await db.refresh(urun)
    return urun


get_owned_record = kullanici_kaydini_al
queue_record = kaydi_kuyruga_ekle
find_or_create_product = urun_bul_veya_olustur
