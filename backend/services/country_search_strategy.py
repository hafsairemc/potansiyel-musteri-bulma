from dataclasses import dataclass


@dataclass(frozen=True)
class UlkeAramaStratejisi:
    buyer_terms: tuple[str, ...]
    platforms: tuple[str, ...]
    market_terms: tuple[str, ...]


CountrySearchStrategy = UlkeAramaStratejisi

STRATEJILER = {
    "çin": UlkeAramaStratejisi(
        buyer_terms=("进口商", "经销商", "批发商", "采购"),
        platforms=("made-in-china.com", "1688.com", "globalsources.com", "alibaba.com"),
        market_terms=("China importer", "Chinese distributor", "采购需求"),
    ),
    "china": UlkeAramaStratejisi(
        buyer_terms=("进口商", "经销商", "批发商", "采购"),
        platforms=("made-in-china.com", "1688.com", "globalsources.com", "alibaba.com"),
        market_terms=("China importer", "Chinese distributor", "采购需求"),
    ),
    "abd": UlkeAramaStratejisi(
        buyer_terms=("importer", "distributor", "wholesaler", "procurement"),
        platforms=("thomasnet.com", "importyeti.com", "globalspec.com", "industrynet.com"),
        market_terms=("United States importer", "US distributor", "purchasing manager"),
    ),
    "united states": UlkeAramaStratejisi(
        buyer_terms=("importer", "distributor", "wholesaler", "procurement"),
        platforms=("thomasnet.com", "importyeti.com", "globalspec.com", "industrynet.com"),
        market_terms=("United States importer", "US distributor", "purchasing manager"),
    ),
}

STRATEGIES = STRATEJILER


def ulke_stratejisi_getir(country: str) -> UlkeAramaStratejisi | None:
    return STRATEJILER.get(country.strip().lower())


strategy_for = ulke_stratejisi_getir
