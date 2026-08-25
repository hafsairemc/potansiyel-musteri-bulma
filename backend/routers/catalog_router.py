from fastapi import APIRouter
from services.country_catalog_service import CountryCatalogService

router = APIRouter(prefix="/catalog", tags=["Catalog"])
katalog_servisi = CountryCatalogService()
catalog = katalog_servisi


@router.get("/countries")
def ulkeleri_listele():
    return {"countries": katalog_servisi.list_countries()}


countries = ulkeleri_listele
