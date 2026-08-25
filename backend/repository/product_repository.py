import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.product_model import (
    ProductCompetitor,
    ProductImage,
    ProductIndustry,
    ProductModel,
    ProductTargetCountry,
)
from schemas.product_schema import ProductCreate


class ProductRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, product_id: uuid.UUID | str, user_id: str) -> ProductModel | None:
        sorgu = select(ProductModel).filter(
            ProductModel.id == str(product_id),
            ProductModel.user_id == user_id,
        )
        sonuc = await self.db.execute(sorgu)
        return sonuc.scalars().first()

    async def get_all(self, user_id: str, skip: int = 0, limit: int = 100):
        sorgu = select(ProductModel).filter(ProductModel.user_id == user_id)
        sonuc = await self.db.execute(sorgu.offset(skip).limit(limit))
        return sonuc.scalars().all()

    async def create(self, product_in: ProductCreate, user_id: str) -> ProductModel:
        yeni_urun = ProductModel(
            user_id=user_id,
            oem=product_in.oem,
            hs_code=product_in.hs_code,
            name_tr=product_in.name_tr,
            name_en=product_in.name_en,
            name_de=product_in.name_de,
            name_fr=product_in.name_fr,
            name_ru=product_in.name_ru,
            name_es=product_in.name_es,
            name_ar=product_in.name_ar,
            description=product_in.description,
            search_profile=product_in.search_profile,
            target_languages=product_in.target_languages,
        )
        self.db.add(yeni_urun)
        await self.db.flush()

        for resim_url in product_in.images:
            resim_modeli = ProductImage(product_id=yeni_urun.id, url=resim_url)
            self.db.add(resim_modeli)

        for rakip_marka in product_in.competitors:
            rakip_modeli = ProductCompetitor(product_id=yeni_urun.id, brand_name=rakip_marka)
            self.db.add(rakip_modeli)

        for sektor_adi in product_in.industries:
            sektor_modeli = ProductIndustry(product_id=yeni_urun.id, industry_name=sektor_adi)
            self.db.add(sektor_modeli)

        for hedef_ulke in product_in.target_countries:
            ulke_modeli = ProductTargetCountry(
                product_id=yeni_urun.id,
                country_name=hedef_ulke.country_name,
                domain_extension=hedef_ulke.domain_extension,
            )
            self.db.add(ulke_modeli)

        urun_id = yeni_urun.id
        await self.db.commit()

        kaydedilen_urun = await self.get_by_id(urun_id, user_id)
        if kaydedilen_urun is None:
            raise RuntimeError("Oluşturulan ürün yeniden okunamadı")
        return kaydedilen_urun

    async def delete(self, product_id: uuid.UUID | str, user_id: str) -> bool:
        urun = await self.get_by_id(product_id, user_id=user_id)
        if urun:
            await self.db.delete(urun)
            await self.db.commit()
            return True
        return False


UrunDeposu = ProductRepository
