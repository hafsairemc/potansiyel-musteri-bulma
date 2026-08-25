from fastapi import HTTPException, status


class UrunBulunamadiHatasi(HTTPException):
    def __init__(self, detay: str = "Ürün bulunamadı."):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detay)


class VeritabaniIslemHatasi(HTTPException):
    def __init__(self, detay: str = "Veritabanı işlemi sırasında hata oluştu."):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detay)


ProductNotFoundException = UrunBulunamadiHatasi
DatabaseOperationException = VeritabaniIslemHatasi
