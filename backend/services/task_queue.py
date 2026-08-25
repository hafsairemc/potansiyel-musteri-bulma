import os
import threading


def _kuyruga_ekle(task_name: str, target, record_id: str) -> None:
    if os.getenv("TASK_QUEUE_MODE", "inline").lower() == "inline":
        threading.Thread(
            target=target,
            args=(record_id,),
            daemon=True,
            name=f"pusula-{task_name.rsplit('.', 1)[-1]}-{record_id[:8]}",
        ).start()
        return

    from workers.celery_app import celery_app
    celery_app.send_task(task_name, args=[record_id])


_enqueue = _kuyruga_ekle


def arama_gorevini_kuyruga_ekle(job_id: str) -> None:
    from workers.tasks import run_search_job
    _enqueue("pusula.run_search_job", run_search_job, job_id)


enqueue_job = arama_gorevini_kuyruga_ekle


def aktarim_gorevini_kuyruga_ekle(export_id: str) -> None:
    from workers.tasks import build_export
    _enqueue("pusula.build_export", build_export, export_id)


enqueue_export = aktarim_gorevini_kuyruga_ekle


def rfq_gorevini_kuyruga_ekle(search_id: str) -> None:
    from workers.tasks import run_rfq_task
    _enqueue("pusula.run_rfq_search", run_rfq_task, search_id)


enqueue_rfq_search = rfq_gorevini_kuyruga_ekle



def fuar_analiz_gorevini_kuyruga_ekle(analysis_id: str) -> None:
    from workers.tasks import run_fair_task
    _enqueue("pusula.run_fair_analysis", run_fair_task, analysis_id)


enqueue_fair_analysis = fuar_analiz_gorevini_kuyruga_ekle


def eposta_kampanya_gorevini_kuyruga_ekle(campaign_id: str) -> None:
    from workers.tasks import run_email_campaign_task
    _enqueue("pusula.run_email_campaign", run_email_campaign_task, campaign_id)


enqueue_email_campaign = eposta_kampanya_gorevini_kuyruga_ekle


def talep_ilani_gorevini_kuyruga_ekle(post_id: str) -> None:
    from workers.tasks import run_demand_post_task
    _enqueue("pusula.run_demand_post", run_demand_post_task, post_id)


enqueue_demand_post = talep_ilani_gorevini_kuyruga_ekle
