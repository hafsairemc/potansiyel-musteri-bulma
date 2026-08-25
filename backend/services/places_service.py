from services.location.overpass_poi_service import OverpassPoiService


class MekanServisi:
    @staticmethod
    def yakindaki_firmayi_bul(lat: float, lon: float) -> str | None:
        sonuc = OverpassPoiService(radius_m=20).en_yakini_bul(lat, lon)
        return sonuc.name if sonuc else None

    find_nearby_company = yakindaki_firmayi_bul


PlacesService = MekanServisi
