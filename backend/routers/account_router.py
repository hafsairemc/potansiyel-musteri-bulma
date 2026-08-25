from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.database import get_async_db
from core.security import get_current_user
from models.crawler_model import SearchBatch
from services.plan_service import PlanService

router = APIRouter(prefix="/account", tags=["Account"])


@router.get("/plans")
def paketleri_listele():
    return PlanService.catalog()


@router.get("/entitlements")
async def kullanim_haklari(
    db: AsyncSession = Depends(get_async_db),
    user: dict = Depends(get_current_user),
):
    kullanici_id = user.get("id") or user.get("sub")
    haklar = PlanService().entitlements(kullanici_id)
    ay_basi = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    sorgu = select(func.count(SearchBatch.id)).where(
        SearchBatch.user_id == kullanici_id,
        SearchBatch.created_at >= ay_basi,
    )
    kullanilan_adet = (await db.execute(sorgu)).scalar_one()

    aylik_limit = haklar.get("monthly_searches")
    kalan_hak = None if aylik_limit is None else max(aylik_limit - kullanilan_adet, 0)

    haklar["usage"] = {
        "used_searches": kullanilan_adet,
        "remaining_searches": kalan_hak,
        "period_start": ay_basi.date().isoformat(),
    }
    return haklar


plans = paketleri_listele
entitlements = kullanim_haklari
