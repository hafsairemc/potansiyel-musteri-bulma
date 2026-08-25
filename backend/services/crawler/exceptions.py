class TarayiciHatasi(Exception):
    """Crawler işlemleri için temel hata sınıfı"""
    pass


CrawlerException = TarayiciHatasi


class RobotsTxtEngellendiHatasi(TarayiciHatasi):
    """Robots.txt tarafından engellendi"""
    pass


RobotsTxtBlockedException = RobotsTxtEngellendiHatasi


class CaptchaHatasi(TarayiciHatasi):
    """CAPTCHA ile karşılaşıldı"""
    pass


CaptchaException = CaptchaHatasi
