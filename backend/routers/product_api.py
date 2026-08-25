import io
import uuid
from typing import Any
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from core.config import settings
from core.database import get_async_db
from core.rate_limit import limiter
from core.security import get_current_user
from models.product_model import ProductImage
from schemas.ai_schema import TranslationRequest, TranslationResponse
from schemas.product_schema import ProductCreate, ProductResponse
from services.ai_translation_service import AITranslationService
from services.category_service import CategoryService
from services.db import admin_supabase
from services.image_keyword_service import ImageKeywordService
from services.product_service import ProductService
from services.reverse_image_search_service import ReverseImageSearchError, ReverseImageSearchService

router = APIRouter(prefix="/v2/products", tags=["Products V2"])


@router.get("/catalog/categories")
def kategorileri_listele():
    return {"categories": CategoryService().list_categories()}


@router.post("/classify")
def urunu_siniflandir(payload: dict):
    urun_adi = str(payload.get("product_name") or "").strip()
    if len(urun_adi) < 2:
        raise HTTPException(status_code=422, detail="Ürün adı en az 2 karakter olmalıdır")
    return CategoryService().classify(urun_adi)


def urun_servisi_al(db: AsyncSession = Depends(get_async_db)):
    return ProductService(db)


get_product_service = urun_servisi_al


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def urun_olustur(
    product_in: ProductCreate,
    service: ProductService = Depends(urun_servisi_al),
    current_user: dict = Depends(get_current_user),
):
    kullanici_id = str(current_user["sub"])
    return await service.create_product(product_in, user_id=kullanici_id)


@router.post("/translate", response_model=TranslationResponse, status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
def urun_adi_cevir(
    request: Request,
    payload: TranslationRequest,
    current_user: dict = Depends(get_current_user),
):
    ai_service = AITranslationService()
    return ai_service.translate_product_name(payload.product_name)


@router.get("/{product_id}", response_model=ProductResponse)
async def urunu_getir(
    product_id: uuid.UUID,
    service: ProductService = Depends(urun_servisi_al),
    current_user: dict = Depends(get_current_user),
):
    return await service.get_product(product_id, user_id=current_user["sub"])


@router.get("", response_model=list[ProductResponse])
async def urunleri_getir(
    skip: int = 0,
    limit: int = 10,
    service: ProductService = Depends(urun_servisi_al),
    current_user: dict = Depends(get_current_user),
):
    return await service.get_products(skip=skip, limit=limit, user_id=current_user["sub"])


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def urun_sil(
    product_id: uuid.UUID,
    service: ProductService = Depends(urun_servisi_al),
    current_user: dict = Depends(get_current_user),
):
    await service.delete_product(product_id, user_id=current_user["sub"])


@router.post("/{product_id}/images", status_code=status.HTTP_201_CREATED)
async def urun_resimleri_yukle(
    product_id: uuid.UUID,
    files: list[UploadFile] = File(...),
    reverse_search: bool = Form(False),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_user),
):
    if not 1 <= len(files) <= 3:
        raise HTTPException(status_code=422, detail="1 ile 3 arasında görsel yükleyin")

    servis = ProductService(db)
    urun = await servis.get_product(product_id, user_id=current_user["sub"])
    if len(urun.images) + len(files) > 3:
        raise HTTPException(status_code=422, detail="Bir üründe en fazla üç görsel bulunabilir")

    if not admin_supabase:
        raise HTTPException(status_code=503, detail="Supabase Storage yapılandırılmamış")

    yuklenenler: list[dict[str, Any]] = []
    resim_terimleri = list((urun.search_profile or {}).get("image_terms") or [])
    analizci = ImageKeywordService()
    ters_arama_sonuclari: list[dict[str, Any]] = []
    ters_arama_durumu = "not_requested"

    for dosya in files:
        icerik = await dosya.read()
        if len(icerik) > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail=f"Görsel {settings.max_upload_mb} MB sınırını aşıyor",
            )

        try:
            resim = Image.open(io.BytesIO(icerik))
            resim.verify()
            medya_tipi = Image.MIME.get(resim.format) if resim.format else None
        except Exception as exc:
            raise HTTPException(status_code=422, detail="Geçersiz görsel dosyası") from exc

        if medya_tipi not in {"image/jpeg", "image/png", "image/webp"}:
            raise HTTPException(status_code=422, detail="Yalnız JPEG, PNG veya WebP desteklenir")

        uzanti = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[medya_tipi]
        dosya_adi = f"{current_user['sub']}/{product_id}/{uuid.uuid4()}.{uzanti}"

        admin_supabase.storage.from_(settings.product_images_bucket).upload(
            dosya_adi, icerik, {"content-type": medya_tipi, "upsert": "false"}
        )

        resim_url = f"storage:{dosya_adi}"
        db.add(ProductImage(product_id=str(product_id), url=resim_url))

        tespit_edilen_terimler = analizci.extract(icerik, medya_tipi)
        resim_terimleri.extend(tespit_edilen_terimler)
        yuklenenler.append({"url": resim_url, "detected_terms": tespit_edilen_terimler})

        if reverse_search and not ters_arama_sonuclari:
            ters_arama_durumu = "completed"
            try:
                imzali = admin_supabase.storage.from_(settings.product_images_bucket).create_signed_url(
                    dosya_adi, 600
                )
                imzali_url = imzali.get("signedURL") or imzali.get("signedUrl") or imzali.get("signed_url")
                if not isinstance(imzali_url, str) or not imzali_url:
                    raise ReverseImageSearchError("Görsel için geçici bağlantı üretilemedi")

                ters_arama_servisi = ReverseImageSearchService()
                ters_arama_sonuclari = ters_arama_servisi.search(imzali_url)
                resim_terimleri.extend(ters_arama_servisi.terms(ters_arama_sonuclari))
            except ReverseImageSearchError as exc:
                ters_arama_durumu = "failed"
                yuklenenler[-1]["reverse_search_error"] = str(exc)

    profil = dict(urun.search_profile or {})
    profil["image_terms"] = list(dict.fromkeys(resim_terimleri))[:16]
    if reverse_search:
        profil["reverse_image_matches"] = ters_arama_sonuclari
    urun.search_profile = profil
    flag_modified(urun, "search_profile")
    await db.commit()

    return {
        "images": yuklenenler,
        "image_terms": profil["image_terms"],
        "reverse_search_status": ters_arama_durumu,
        "reverse_image_matches": ters_arama_sonuclari,
    }


list_categories = kategorileri_listele
classify_product = urunu_siniflandir
create_product = urun_olustur
translate_product = urun_adi_cevir
get_product = urunu_getir
get_products = urunleri_getir
delete_product = urun_sil
upload_product_images = urun_resimleri_yukle
