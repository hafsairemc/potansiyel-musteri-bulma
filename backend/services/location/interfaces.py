from abc import ABC, abstractmethod
from schemas.location_schema import IPResult, POIResult


class IMekanSaglayici(ABC):
    SAGLAYICI_ADI: str = "unknown"
    PROVIDER_NAME = SAGLAYICI_ADI

    @abstractmethod
    def en_yakini_bul(self, lat: float, lon: float) -> POIResult | None:
        raise NotImplementedError

    find_nearest = en_yakini_bul


IPoiProvider = IMekanSaglayici


class IIpSaglayici(ABC):
    SAGLAYICI_ADI: str = "unknown"
    PROVIDER_NAME = SAGLAYICI_ADI

    @abstractmethod
    def coz(self, ip_address: str) -> IPResult | None:
        raise NotImplementedError

    lookup = coz


IIpProvider = IIpSaglayici
