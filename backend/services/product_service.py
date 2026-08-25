import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from repository.product_repository import ProductRepository
from schemas.product_schema import ProductCreate, ProductResponse
from core.exceptions import ProductNotFoundException, DatabaseOperationException

logger = logging.getLogger(__name__)


class UrunServisi:
    def __init__(self, db: AsyncSession):
        self.repository = ProductRepository(db)

    async def urun_olustur(self, product_in: ProductCreate, user_id: str) -> ProductResponse:
        try:
            return await self.repository.create(product_in, user_id=user_id)
        except Exception as exc:
            logger.exception("Ürün oluşturulamadı")
            raise DatabaseOperationException() from exc

    create_product = urun_olustur

    async def urunu_getir(self, product_id: uuid.UUID, user_id: str) -> ProductResponse:
        urun = await self.repository.get_by_id(product_id, user_id=user_id)
        if not urun:
            raise ProductNotFoundException(detail=f"{product_id} ID'li ürün bulunamadı.")
        return urun

    get_product = urunu_getir

    async def urunleri_getir(self, user_id: str, skip: int = 0, limit: int = 100):
        return await self.repository.get_all(user_id=user_id, skip=skip, limit=limit)

    get_products = urunleri_getir

    async def urunu_sil(self, product_id: uuid.UUID, user_id: str):
        basarili = await self.repository.delete(product_id, user_id=user_id)
        if not basarili:
            raise ProductNotFoundException(detail="Silinmek istenen ürün bulunamadı.")

    delete_product = urunu_sil


ProductService = UrunServisi
