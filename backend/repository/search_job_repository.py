from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.crawler_model import CrawlerSearchJob
from models.schemas import SearchJobCreate


class SearchJobRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, job_id: str, user_id: str) -> CrawlerSearchJob | None:
        sorgu = select(CrawlerSearchJob).filter(
            CrawlerSearchJob.id == job_id,
            CrawlerSearchJob.user_id == user_id,
        )
        sonuc = await self.db.execute(sorgu)
        return sonuc.scalars().first()

    async def get_all(self, user_id: str, skip: int = 0, limit: int = 100):
        sorgu = select(CrawlerSearchJob).filter(CrawlerSearchJob.user_id == user_id)
        sonuc = await self.db.execute(sorgu.offset(skip).limit(limit))
        return sonuc.scalars().all()

    async def create(self, job_in: SearchJobCreate, user_id: str) -> CrawlerSearchJob:
        yeni_gorev = CrawlerSearchJob(
            user_id=user_id,
            product_id=job_in.product_id,
            search_query=job_in.search_query,
            target_country=job_in.target_country,
            search_engine=job_in.search_engine,
            status="PENDING",
        )
        self.db.add(yeni_gorev)
        await self.db.commit()
        await self.db.refresh(yeni_gorev)
        return yeni_gorev

    async def update_status(
        self,
        gorev: CrawlerSearchJob,
        status: str,
        report_url: str | None = None,
    ) -> CrawlerSearchJob:
        gorev.status = status
        if report_url:
            gorev.report_url = report_url
        if status in ["COMPLETED", "FAILED", "CANCELLED"]:
            gorev.end_time = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(gorev)
        return gorev


AramaGoreviDeposu = SearchJobRepository
