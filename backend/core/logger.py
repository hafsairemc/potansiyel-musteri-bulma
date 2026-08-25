import logging


def setup_logger(isim: str = "pusula"):
    gunlukcu = logging.getLogger(isim)
    if not gunlukcu.handlers:
        yonetici = logging.StreamHandler()
        bicimlendirici = logging.Formatter("[%(levelname)s] %(asctime)s - %(message)s")
        yonetici.setFormatter(bicimlendirici)
        gunlukcu.addHandler(yonetici)
        gunlukcu.setLevel(logging.INFO)
    return gunlukcu


logger = setup_logger()
gunlukcu = logger
