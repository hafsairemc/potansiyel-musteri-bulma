from dataclasses import asdict, dataclass
import pycountry


@dataclass(frozen=True)
class UlkeBilgisi:
    code: str
    name: str
    domain: str
    languages: tuple[str, ...]
    cities: tuple[str, ...]


CountryInfo = UlkeBilgisi

ONCELIKLI_ULKELER = (
    UlkeBilgisi("TR", "Türkiye", ".tr", ("Türkçe", "İngilizce"), ("İstanbul", "Ankara", "İzmir", "Bursa", "Antalya", "Mersin", "Adana", "Gaziantep")),
    UlkeBilgisi("DE", "Almanya", ".de", ("Almanca", "İngilizce"), ("Berlin", "Hamburg", "Münih", "Köln", "Frankfurt")),
    UlkeBilgisi("US", "ABD", ".com", ("İngilizce", "İspanyolca"), ("New York", "Los Angeles", "Chicago", "Houston", "Miami")),
    UlkeBilgisi("GB", "Birleşik Krallık", ".co.uk", ("İngilizce",), ("London", "Birmingham", "Manchester", "Glasgow", "Liverpool")),
    UlkeBilgisi("AE", "BAE", ".ae", ("Arapça", "İngilizce"), ("Dubai", "Abu Dhabi", "Sharjah")),
    UlkeBilgisi("SA", "Suudi Arabistan", ".sa", ("Arapça", "İngilizce"), ("Riyadh", "Jeddah", "Dammam")),
    UlkeBilgisi("FR", "Fransa", ".fr", ("Fransızca", "İngilizce"), ("Paris", "Lyon", "Marseille", "Toulouse")),
    UlkeBilgisi("ES", "İspanya", ".es", ("İspanyolca", "İngilizce"), ("Madrid", "Barcelona", "Valencia", "Sevilla")),
    UlkeBilgisi("IT", "İtalya", ".it", ("İtalyanca", "İngilizce"), ("Milano", "Roma", "Torino", "Bologna")),
    UlkeBilgisi("RU", "Rusya", ".ru", ("Rusça",), ("Moscow", "Saint Petersburg", "Kazan")),
    UlkeBilgisi("CN", "Çin", ".cn", ("Çince", "İngilizce"), ("Shanghai", "Beijing", "Guangzhou", "Shenzhen", "Ningbo")),
    UlkeBilgisi("IN", "Hindistan", ".in", ("İngilizce", "Hintçe"), ("Mumbai", "Delhi", "Bengaluru", "Chennai", "Ahmedabad")),
    UlkeBilgisi("JP", "Japonya", ".jp", ("Japonca", "İngilizce"), ("Tokyo", "Osaka", "Nagoya")),
    UlkeBilgisi("KR", "Güney Kore", ".kr", ("Korece", "İngilizce"), ("Seoul", "Busan", "Incheon")),
    UlkeBilgisi("AZ", "Azerbaycan", ".az", ("Azerice", "Rusça"), ("Bakü", "Gence")),
    UlkeBilgisi("GE", "Gürcistan", ".ge", ("Gürcüce", "İngilizce"), ("Tiflis", "Batum")),
    UlkeBilgisi("BG", "Bulgaristan", ".bg", ("Bulgarca", "İngilizce"), ("Sofya", "Plovdiv", "Varna")),
    UlkeBilgisi("NL", "Hollanda", ".nl", ("Felemenkçe", "İngilizce"), ("Amsterdam", "Rotterdam", "Eindhoven")),
    UlkeBilgisi("BE", "Belçika", ".be", ("Fransızca", "Felemenkçe", "İngilizce"), ("Brussels", "Antwerp", "Ghent")),
    UlkeBilgisi("PL", "Polonya", ".pl", ("Lehçe", "İngilizce"), ("Warsaw", "Krakow", "Wroclaw")),
    UlkeBilgisi("RO", "Romanya", ".ro", ("Romence", "İngilizce"), ("Bucharest", "Cluj-Napoca", "Timisoara")),
    UlkeBilgisi("BR", "Brezilya", ".br", ("Portekizce", "İngilizce"), ("São Paulo", "Rio de Janeiro", "Curitiba")),
    UlkeBilgisi("MX", "Meksika", ".mx", ("İspanyolca", "İngilizce"), ("Mexico City", "Monterrey", "Guadalajara")),
    UlkeBilgisi("CA", "Kanada", ".ca", ("İngilizce", "Fransızca"), ("Toronto", "Montreal", "Vancouver")),
    UlkeBilgisi("AU", "Avustralya", ".au", ("İngilizce",), ("Sydney", "Melbourne", "Brisbane")),
    UlkeBilgisi("ZA", "Güney Afrika", ".za", ("İngilizce",), ("Johannesburg", "Cape Town", "Durban")),
    UlkeBilgisi("EG", "Mısır", ".eg", ("Arapça", "İngilizce"), ("Cairo", "Alexandria")),
)

PRIORITY_COUNTRIES = ONCELIKLI_ULKELER


class UlkeKatalogServisi:
    def __init__(self):
        oncelikli_kodlar = {ulke.code: ulke for ulke in ONCELIKLI_ULKELER}
        kalanlar = []
        for kayit in pycountry.countries:
            kod = kayit.alpha_2.upper()
            if kod in oncelikli_kodlar:
                continue
            isim = kayit.name
            kalanlar.append(UlkeBilgisi(
                code=kod,
                name=isim,
                domain=f".{kod.lower()}",
                languages=("İngilizce",),
                cities=(isim,),
            ))
        self._countries = ONCELIKLI_ULKELER + tuple(sorted(kalanlar, key=lambda oge: oge.name.casefold()))
        self._by_code = {ulke.code: ulke for ulke in self._countries}

    def ulkeleri_listele(self) -> list[dict]:
        return [self._sozluk_yap(ulke) for ulke in self._countries]

    list_countries = ulkeleri_listele

    def ulke_bul(self, name: str) -> UlkeBilgisi | None:
        duzenlenmis = name.casefold().strip()
        if not duzenlenmis:
            return None
        dogrudan = next(
            (ulke for ulke in self._countries if ulke.name.casefold() == duzenlenmis),
            None,
        )
        if dogrudan:
            return dogrudan
        koda_gore = self._by_code.get(name.strip().upper())
        if koda_gore:
            return koda_gore
        try:
            kayit = pycountry.countries.lookup(name.strip())
        except LookupError:
            return None
        return self._by_code.get(kayit.alpha_2.upper())

    find = ulke_bul

    @staticmethod
    def _sozluk_yap(country: UlkeBilgisi) -> dict:
        veri = asdict(country)
        veri["languages"] = list(country.languages)
        veri["cities"] = list(country.cities)
        return veri

    _serialize = _sozluk_yap


CountryCatalogService = UlkeKatalogServisi
