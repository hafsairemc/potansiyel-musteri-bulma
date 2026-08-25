from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.database import get_async_db
from core.security import get_current_user
from models.growth_model import LearningAttempt, LearningProgress
from schemas.growth_schema import LessonAnswerBody, ProgressBody
from services.learning_service import (
    LESSONS,
    answer_is_correct,
    lesson_by_key,
    public_lesson,
)
from services.plan_service import PlanService

router = APIRouter(prefix="/learning", tags=["Learning"])


async def _ilerlemeyi_getir(
    db: AsyncSession,
    user_id: str,
    lesson_key: str,
) -> LearningProgress | None:
    return (
        await db.execute(
            select(LearningProgress).where(
                LearningProgress.user_id == user_id,
                LearningProgress.lesson_key == lesson_key,
            )
        )
    ).scalar_one_or_none()


_get_progress = _ilerlemeyi_getir


def _ders_var_mi_kontrol(lesson_key: str) -> None:
    if not lesson_by_key(lesson_key):
        raise HTTPException(404, "Ders bulunamadı")


_require_lesson = _ders_var_mi_kontrol


@router.get("/lessons")
async def dersleri_listele(
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    ilerleme_satirlari = (
        await db.execute(
            select(LearningProgress).where(
                LearningProgress.user_id == user["sub"]
            )
        )
    ).scalars().all()

    deneme_satirlari = (
        await db.execute(
            select(
                LearningAttempt.lesson_key,
                func.count(LearningAttempt.id),
            )
            .where(LearningAttempt.user_id == user["sub"])
            .group_by(LearningAttempt.lesson_key)
        )
    ).all()

    ilerleme = {satir.lesson_key: satir for satir in ilerleme_satirlari}
    denemeler = dict(deneme_satirlari)

    return [
        {
            **public_lesson(ders),
            "progress": (
                ilerleme[ders["key"]].progress
                if ders["key"] in ilerleme
                else 0
            ),
            "completed": (
                ilerleme[ders["key"]].completed
                if ders["key"] in ilerleme
                else False
            ),
            "attempt_count": denemeler.get(ders["key"], 0),
        }
        for ders in LESSONS
    ]


@router.put("/lessons/{lesson_key}/progress")
async def ders_ilerlemesini_guncelle(
    lesson_key: str,
    body: ProgressBody,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    PlanService().ensure_module(user["sub"], "learning")
    _ders_var_mi_kontrol(lesson_key)

    if body.progress == 100:
        raise HTTPException(
            422,
            "Dersi tamamlamak için kontrol sorusunu cevaplayın",
        )

    kayit = await _ilerlemeyi_getir(db, user["sub"], lesson_key)
    if kayit is None:
        kayit = LearningProgress(user_id=user["sub"], lesson_key=lesson_key)
        db.add(kayit)

    if not kayit.completed:
        kayit.progress = max(kayit.progress or 0, body.progress)

    await db.commit()
    return {
        "lesson_key": lesson_key,
        "progress": kayit.progress,
        "completed": kayit.completed,
    }


@router.post("/lessons/{lesson_key}/complete")
async def dersi_tamamla(
    lesson_key: str,
    body: LessonAnswerBody,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    PlanService().ensure_module(user["sub"], "learning")
    _ders_var_mi_kontrol(lesson_key)

    kayit = await _ilerlemeyi_getir(db, user["sub"], lesson_key)
    if kayit is None or kayit.progress < 80:
        raise HTTPException(
            409,
            "Kontrol sorusundan önce ders içeriğini okuduğunuzu onaylayın",
        )

    dogru_mu = answer_is_correct(lesson_key, body.answer_index)
    db.add(
        LearningAttempt(
            user_id=user["sub"],
            lesson_key=lesson_key,
            answer_index=body.answer_index,
            correct=dogru_mu,
        )
    )

    if not dogru_mu:
        await db.commit()
        raise HTTPException(
            422,
            "Cevap doğru değil. Ders içeriğini tekrar inceleyin",
        )

    kayit.progress = 100
    kayit.completed = True
    await db.commit()

    return {
        "lesson_key": lesson_key,
        "progress": 100,
        "completed": True,
    }


learning_lessons = dersleri_listele
update_learning_progress = ders_ilerlemesini_guncelle
complete_lesson = dersi_tamamla
