from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.database import get_async_db
from core.security import get_current_user
from models.growth_model import TradeMarketSnapshot
from models.product_model import ProductModel
from routers.intelligence_common import urun_bul_veya_olustur
from schemas.growth_schema import TradeMarketBody
from services.country_catalog_service import CountryCatalogService
from services.plan_service import PlanService
from services.un_comtrade_service import TradeDataError, UNComtradeService

router = APIRouter(prefix="/trade-markets", tags=["Trade Market Data"])


def piyasa_verisini_sozluk_yap(kayit: TradeMarketSnapshot) -> dict:
    return {
        "id": kayit.id,
        "product_id": kayit.product_id,
        "target_country": kayit.target_country,
        "reporter_name": kayit.reporter_name,
        "hs_code": kayit.hs_code,
        "commodity": kayit.commodity,
        "period": kayit.period,
        "import_value_usd": kayit.import_value_usd,
        "net_weight_kg": kayit.net_weight_kg,
        "quantity": kayit.quantity,
        "source_url": kayit.source_url,
    }


serialize_snapshot = piyasa_verisini_sozluk_yap


@router.post("/analyze")
async def pazar_verisini_analiz_et(
    body: TradeMarketBody,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    PlanService().ensure_module(user["sub"], "trade_data")
    urun = await urun_bul_veya_olustur(db, user["sub"], body.product_id)
    gtip = urun.hs_code or (body.product_id.strip() if body.product_id.strip().replace(".", "").isdigit() else None)
    if not gtip:
        gtip = "8708.30"  # Varsayılan otomotiv/genel GTİP fallback
        urun.hs_code = gtip
        await db.commit()

    ulke = CountryCatalogService().find(body.target_country)
    if ulke is None:
        raise HTTPException(422, "Hedef ülke ülke kataloğunda bulunamadı")

    try:
        veri = await UNComtradeService().imports(ulke.code, urun.hs_code, body.year)
    except TradeDataError as exc:
        raise HTTPException(503, str(exc)) from exc

    kayit = (
        await db.execute(
            select(TradeMarketSnapshot).where(
                TradeMarketSnapshot.user_id == user["sub"],
                TradeMarketSnapshot.product_id == urun.id,
                TradeMarketSnapshot.target_country == ulke.name,
                TradeMarketSnapshot.period == veri["period"],
                TradeMarketSnapshot.hs_code == veri["hs_code"],
            )
        )
    ).scalar_one_or_none()

    if kayit is None:
        kayit = TradeMarketSnapshot(
            user_id=user["sub"],
            product_id=urun.id,
            target_country=ulke.name,
            period=veri["period"],
            hs_code=veri["hs_code"],
            reporter_code=veri["reporter_code"],
            source_url=veri["source_url"],
            import_value_usd=veri["import_value_usd"],
        )
        db.add(kayit)

    kayit.reporter_name = veri["reporter_name"]
    kayit.commodity = veri["commodity"]
    kayit.import_value_usd = veri["import_value_usd"]
    kayit.net_weight_kg = veri["net_weight_kg"]
    kayit.quantity = veri["quantity"]
    kayit.source_url = veri["source_url"]
    await db.commit()
    await db.refresh(kayit)

    return piyasa_verisini_sozluk_yap(kayit)


@router.get("")
async def pazar_verilerini_listele(
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    satirlar = (
        await db.execute(
            select(TradeMarketSnapshot)
            .where(TradeMarketSnapshot.user_id == user["sub"])
            .order_by(TradeMarketSnapshot.created_at.desc())
            .limit(100)
        )
    ).scalars().all()
    return [piyasa_verisini_sozluk_yap(satir) for satir in satirlar]


analyze_trade_market = pazar_verisini_analiz_et
list_trade_markets = pazar_verilerini_listele
