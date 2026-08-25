from datetime import datetime
from urllib.parse import urlencode
import httpx
import pycountry

M49_KODLARI = {
    "TR": 792, "DE": 276, "US": 842, "GB": 826, "FR": 250, "IT": 380,
    "ES": 724, "NL": 528, "BE": 56, "PL": 616, "RO": 642, "BG": 100,
    "GR": 300, "GE": 268, "AZ": 31, "RU": 643, "UA": 804, "SA": 682,
    "AE": 784, "QA": 634, "EG": 818, "MA": 504, "DZ": 12, "CN": 156,
    "JP": 392, "IN": 356, "BR": 76,
}
M49_CODES = M49_KODLARI


class TicaretVeriHatasi(RuntimeError):
    pass


TradeDataError = TicaretVeriHatasi


class BirlesmisMilletlerTicaretServisi:
    ENDPOINT = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"

    async def ithalat_verilerini_getir(self, reporter_code: str, hs_code: str, year: int | None = None) -> dict:
        kod = reporter_code.upper()
        kayit = pycountry.countries.get(alpha_2=kod)
        m49 = int(kayit.numeric) if kayit and getattr(kayit, "numeric", None) else M49_KODLARI.get(kod)
        normallestirilmis_gtip = "".join(karakter for karakter in hs_code if karakter.isdigit())[:6]

        if not m49:
            raise TicaretVeriHatasi("Bu ülke için UN Comtrade kodu tanımlı değil")
        if len(normallestirilmis_gtip) not in {2, 4, 6}:
            raise TicaretVeriHatasi("Ticaret analizi için 2, 4 veya 6 haneli GTİP gereklidir")

        en_son_yil = year or datetime.utcnow().year - 1
        donemler = ",".join(str(deger) for deger in range(en_son_yil, en_son_yil - 3, -1))
        parametreler = {
            "reportercode": m49,
            "period": donemler,
            "flowCode": "M",
            "cmdCode": normallestirilmis_gtip,
            "partnerCode": 0,
            "maxRecords": 10,
            "includeDesc": "true",
        }

        try:
            async with httpx.AsyncClient(timeout=15) as istemci:
                yanit = await istemci.get(self.ENDPOINT, params=parametreler)
                if yanit.status_code == 429:
                    raise TicaretVeriHatasi("UN Comtrade ücretsiz API kotası geçici olarak dolu")
                yanit.raise_for_status()
                veri = yanit.json()
        except TicaretVeriHatasi:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise TicaretVeriHatasi("UN Comtrade verisine ulaşılamadı") from exc

        satirlar = veri.get("data") or []
        if not satirlar:
            raise TicaretVeriHatasi("Seçilen ülke, dönem ve GTİP için ticaret verisi bulunamadı")

        en_guncel = max(satirlar, key=lambda oge: int(oge.get("period") or 0))
        return {
            "reporter_code": str(m49),
            "reporter_name": en_guncel.get("reporterDesc"),
            "hs_code": normallestirilmis_gtip,
            "commodity": en_guncel.get("cmdDesc") or en_guncel.get("cmdCode"),
            "period": int(en_guncel.get("period")),
            "import_value_usd": float(en_guncel.get("primaryValue") or 0),
            "net_weight_kg": float(en_guncel.get("netWgt") or 0) if en_guncel.get("netWgt") is not None else None,
            "quantity": float(en_guncel.get("qty") or 0) if en_guncel.get("qty") is not None else None,
            "is_aggregate": en_guncel.get("isAggregate"),
            "source_url": f"{self.ENDPOINT}?{urlencode(parametreler)}",
        }

    imports = ithalat_verilerini_getir


UNComtradeService = BirlesmisMilletlerTicaretServisi
