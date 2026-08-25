import os
import re
import httpx


class TersineGorselAramaHatasi(RuntimeError):
    pass


ReverseImageSearchError = TersineGorselAramaHatasi


class TersineGorselAramaServisi:
    endpoint = "https://google.serper.dev/lens"

    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY", "")

    def ara(self, image_url: str) -> list[dict]:
        if not self.api_key:
            raise TersineGorselAramaHatasi("Serper API anahtarı yapılandırılmamış")
        try:
            yanit = httpx.post(
                self.endpoint,
                headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
                json={"url": image_url},
                timeout=25,
            )
            if yanit.status_code == 429:
                raise TersineGorselAramaHatasi("Tersine görsel arama kotası dolu")
            yanit.raise_for_status()
            return self.ayristir(yanit.json())
        except TersineGorselAramaHatasi:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise TersineGorselAramaHatasi("Tersine görsel arama tamamlanamadı") from exc

    search = ara

    @staticmethod
    def ayristir(payload: dict) -> list[dict]:
        satirlar = payload.get("visualMatches") or payload.get("exactMatches") or []
        eslesmeler = []
        for satir in satirlar[:20]:
            baglanti = satir.get("link") or satir.get("sourceUrl") or ""
            if not baglanti.startswith("http"):
                continue
            eslesmeler.append({
                "title": str(satir.get("title") or satir.get("name") or "").strip(),
                "source_url": baglanti,
                "image_url": satir.get("imageUrl") or satir.get("thumbnailUrl"),
                "source": satir.get("source") or satir.get("domain") or "Google Lens",
            })
        return eslesmeler

    parse = ayristir

    @staticmethod
    def terimler(matches: list[dict]) -> list[str]:
        kelimeler: list[str] = []
        for eslesme in matches[:10]:
            baslik = re.sub(r"[^\w\s-]", " ", eslesme.get("title") or "", flags=re.UNICODE)
            aday = " ".join(baslik.split()[:8]).strip()
            if len(aday) >= 3 and aday.casefold() not in {oge.casefold() for oge in kelimeler}:
                kelimeler.append(aday)
        return kelimeler[:8]

    terms = terimler


ReverseImageSearchService = TersineGorselAramaServisi
