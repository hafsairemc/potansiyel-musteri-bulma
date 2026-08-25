import logging
import uuid
from datetime import datetime

from core.database import SessionLocal
from models.visitor_model import VisitorModel

logger = logging.getLogger(__name__)


class ZiyaretciServisi:
    @staticmethod
    def ziyaretciyi_veritabanina_kaydet(visitor_data: dict):
        db = SessionLocal()
        try:
            ziyaretci = VisitorModel(
                permission=str(visitor_data.get("permission")),
                country=visitor_data.get("country"),
                city=visitor_data.get("city"),
                formatted_address=visitor_data.get("formatted_address"),
                latitude=visitor_data.get("latitude"),
                longitude=visitor_data.get("longitude"),
                ip=visitor_data.get("ip"),
                operator=visitor_data.get("operator") or visitor_data.get("company"),
                detection_method=visitor_data.get("detection_method"),
                confidence=visitor_data.get("confidence"),
                retention_until=visitor_data.get("retention_until"),
            )
            db.add(ziyaretci)
            db.commit()
            db.refresh(ziyaretci)
            logger.info("Ziyaretçi kaydedildi: %s", ziyaretci.id)
            return ziyaretci.id
        except Exception as exc:
            db.rollback()
            logger.warning("Ziyaretçi kaydedilemedi: %s", exc)
            return None
        finally:
            db.close()

    save_visitor_to_db = ziyaretciyi_veritabanina_kaydet

    @staticmethod
    def suresi_dolanlari_sil() -> int:
        db = SessionLocal()
        try:
            silinen_sayisi = db.query(VisitorModel).filter(
                VisitorModel.retention_until < datetime.utcnow()
            ).delete(synchronize_session=False)
            db.commit()
            return silinen_sayisi
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    delete_expired = suresi_dolanlari_sil

    @staticmethod
    def idye_gore_sil(visitor_id: str) -> bool:
        try:
            normallestirilmis_id = str(uuid.UUID(visitor_id))
        except (ValueError, TypeError, AttributeError):
            return False

        db = SessionLocal()
        try:
            silinen_sayisi = db.query(VisitorModel).filter(
                VisitorModel.id == normallestirilmis_id
            ).delete(synchronize_session=False)
            db.commit()
            return silinen_sayisi == 1
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    delete_by_id = idye_gore_sil


VisitorService = ZiyaretciServisi
