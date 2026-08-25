from datetime import datetime
from sqlalchemy import func, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.visitor_model import VisitorModel, VisitorNotification


class ZiyaretciGelenKutusuServisi:
    def __init__(self, backfill_limit: int = 500):
        self.backfill_limit = backfill_limit

    async def kullanici_icin_listele(
        self,
        db: AsyncSession,
        user_id: str,
        page: int,
        page_size: int,
        unread_only: bool,
    ) -> dict:
        await self._gecmisi_doldur(db, user_id)
        kosullar = [VisitorNotification.user_id == user_id]
        if unread_only:
            kosullar.append(VisitorNotification.read_at.is_(None))

        toplam = (
            await db.execute(
                select(func.count(VisitorNotification.id)).where(*kosullar)
            )
        ).scalar_one()

        okunmamis_sayisi = (
            await db.execute(
                select(func.count(VisitorNotification.id)).where(
                    VisitorNotification.user_id == user_id,
                    VisitorNotification.read_at.is_(None),
                )
            )
        ).scalar_one()

        satirlar = (
            await db.execute(
                select(VisitorNotification, VisitorModel)
                .join(VisitorModel, VisitorModel.id == VisitorNotification.visitor_id)
                .where(*kosullar)
                .order_by(VisitorNotification.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()

        return {
            "page": page,
            "page_size": page_size,
            "total": toplam,
            "unread_count": okunmamis_sayisi,
            "notifications": [
                self._sozluge_donustur(bildirim, ziyaretci)
                for bildirim, ziyaretci in satirlar
            ],
        }

    list_for_user = kullanici_icin_listele

    async def okundu_olarak_isaretle(
        self,
        db: AsyncSession,
        user_id: str,
        notification_id: str,
    ) -> bool:
        sonuc = await db.execute(
            update(VisitorNotification)
            .where(
                VisitorNotification.id == notification_id,
                VisitorNotification.user_id == user_id,
            )
            .values(read_at=datetime.now())
        )
        await db.commit()
        return bool(getattr(sonuc, "rowcount", 0))

    mark_read = okundu_olarak_isaretle

    async def tumunu_okundu_yap(self, db: AsyncSession, user_id: str) -> int:
        await self._gecmisi_doldur(db, user_id)
        sonuc = await db.execute(
            update(VisitorNotification)
            .where(
                VisitorNotification.user_id == user_id,
                VisitorNotification.read_at.is_(None),
            )
            .values(read_at=datetime.now())
        )
        await db.commit()
        return getattr(sonuc, "rowcount", 0) or 0

    mark_all_read = tumunu_okundu_yap

    async def _gecmisi_doldur(self, db: AsyncSession, user_id: str) -> None:
        mevcutlar = select(VisitorNotification.visitor_id).where(
            VisitorNotification.user_id == user_id
        )
        ziyaretci_idleri = (
            await db.execute(
                select(VisitorModel.id)
                .where(
                    VisitorModel.id.not_in(mevcutlar),
                    or_(
                        VisitorModel.country.is_not(None),
                        VisitorModel.city.is_not(None),
                        VisitorModel.operator.is_not(None),
                    ),
                )
                .order_by(VisitorModel.created_at.desc())
                .limit(self.backfill_limit)
            )
        ).scalars().all()

        if not ziyaretci_idleri:
            return

        simdi = datetime.now()
        db.add_all(
            VisitorNotification(
                visitor_id=ziyaretci_id,
                user_id=user_id,
                created_at=simdi,
            )
            for ziyaretci_id in ziyaretci_idleri
        )
        await db.commit()

    _backfill = _gecmisi_doldur

    @staticmethod
    def _sozluge_donustur(notification: VisitorNotification, visitor: VisitorModel) -> dict:
        return {
            "id": notification.id,
            "visitor_id": visitor.id,
            "country": visitor.country,
            "city": visitor.city,
            "company_candidate": visitor.operator,
            "detection_method": visitor.detection_method,
            "confidence": visitor.confidence,
            "permission": visitor.permission,
            "read_at": notification.read_at,
            "created_at": visitor.created_at,
        }

    _serialize = _sozluge_donustur


VisitorInboxService = ZiyaretciGelenKutusuServisi
