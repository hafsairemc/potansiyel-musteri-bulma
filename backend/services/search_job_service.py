from sqlalchemy.ext.asyncio import AsyncSession
from repository.search_job_repository import SearchJobRepository
from models.schemas import SearchJobCreate


class AramaGorevServisi:
    def __init__(self, db: AsyncSession):
        self.repository = SearchJobRepository(db)

    async def gorev_olustur(self, job_in: SearchJobCreate, user_id: str):
        return await self.repository.create(job_in, user_id)

    create_job = gorev_olustur

    async def gorevi_getir(self, job_id: str, user_id: str):
        return await self.repository.get_by_id(job_id, user_id=user_id)

    get_job = gorevi_getir

    async def tum_gorevleri_getir(self, user_id: str, skip: int = 0, limit: int = 100):
        return await self.repository.get_all(user_id=user_id, skip=skip, limit=limit)

    get_all_jobs = tum_gorevleri_getir

    async def gorevi_baslat(self, job_id: str, user_id: str):
        islem = await self.gorevi_getir(job_id, user_id=user_id)
        if not islem:
            raise ValueError("Arama görevi bulunamadı")

        if islem.status != "PENDING":
            raise ValueError(f"Arama görevi zaten {islem.status} durumunda")
        return await self.repository.update_status(islem, "RUNNING")

    start_job = gorevi_baslat

    async def beklemede_olarak_isaretle(self, job):
        return await self.repository.update_status(job, "PENDING")

    mark_pending = beklemede_olarak_isaretle


SearchJobService = AramaGorevServisi
