import os
import secrets
import smtplib
from datetime import datetime
from email.message import EmailMessage
from email.utils import make_msgid
from html import escape

from core.database import SessionLocal
from models.growth_model import EmailCampaign, EmailRecipient


def smtp_yapilandirilmis_mi() -> bool:
    return all(
        os.getenv(name)
        for name in (
            "SMTP_HOST",
            "SMTP_PORT",
            "SMTP_USERNAME",
            "SMTP_PASSWORD",
            "SMTP_FROM_EMAIL",
        )
    )


smtp_is_configured = smtp_yapilandirilmis_mi


def _kisisellestir(template: str, recipient: EmailRecipient) -> str:
    degerler = {
        "name": recipient.full_name or "Yetkili",
        "company": recipient.company_name or "firmanız",
        "email": recipient.email,
    }
    islenmis = template
    for anahtar, deger in degerler.items():
        islenmis = islenmis.replace("{{" + anahtar + "}}", deger)
    return islenmis


_personalize = _kisisellestir


def _mesaj_baglantilari(recipient: EmailRecipient) -> tuple[str, str]:
    recipient.unsubscribe_token = recipient.unsubscribe_token or secrets.token_urlsafe(32)
    recipient.tracking_token = getattr(
        recipient, "tracking_token", None
    ) or secrets.token_urlsafe(32)
    temel_url = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
    return (
        f"{temel_url}/api/email/unsubscribe/{recipient.unsubscribe_token}",
        f"{temel_url}/api/email/open/{recipient.tracking_token}.gif",
    )


_message_urls = _mesaj_baglantilari


def mesaji_olustur(template: str, recipient: EmailRecipient) -> str:
    cikis_url, _ = _mesaj_baglantilari(recipient)
    return (
        f"{_kisisellestir(template, recipient)}\n\n"
        f"Bu iletileri almak istemiyorsanız: {cikis_url}"
    )


render_message = mesaji_olustur


def html_mesajini_olustur(template: str, recipient: EmailRecipient) -> str:
    cikis_url, takip_url = _mesaj_baglantilari(recipient)
    icerik = escape(_kisisellestir(template, recipient)).replace("\n", "<br>")
    return (
        f"<div>{icerik}</div>"
        f'<p><a href="{escape(cikis_url, quote=True)}">Abonelikten çık</a></p>'
        f'<img src="{escape(takip_url, quote=True)}" width="1" height="1" '
        'alt="" style="display:block">'
    )


render_html_message = html_mesajini_olustur


def kampanya_metrikleri(recipients) -> dict[str, int]:
    satirlar = list(recipients)
    return {
        "total": len(satirlar),
        "sent": sum(item.sent_at is not None for item in satirlar),
        "delivered": sum(
            getattr(item, "delivered_at", None) is not None for item in satirlar
        ),
        "bounced": sum(getattr(item, "bounced_at", None) is not None for item in satirlar),
        "complained": sum(
            getattr(item, "complained_at", None) is not None for item in satirlar
        ),
        "failed": sum(item.status == "FAILED" for item in satirlar),
        "opened": sum(item.opened_at is not None for item in satirlar),
        "unsubscribed": sum(item.unsubscribed_at is not None for item in satirlar),
        "replied": sum(getattr(item, "replied_at", None) is not None for item in satirlar),
    }


campaign_metrics = kampanya_metrikleri


def kampanyayi_gonder(campaign_id: str) -> None:
    db = SessionLocal()
    kampanya = db.query(EmailCampaign).filter(EmailCampaign.id == campaign_id).first()
    if not kampanya or kampanya.status != "QUEUED":
        db.close()
        return
    if not smtp_yapilandirilmis_mi():
        kampanya.status = "FAILED"
        db.commit()
        db.close()
        return

    kampanya.status = "SENDING"
    db.commit()
    try:
        with smtplib.SMTP(
            os.environ["SMTP_HOST"], int(os.environ["SMTP_PORT"]), timeout=20
        ) as istemci:
            istemci.starttls()
            istemci.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
            for alici in kampanya.recipients:
                if alici.status != "PENDING" or alici.unsubscribed_at:
                    alici.status = "UNSUBSCRIBED"
                    continue
                mesaj = EmailMessage()
                mesaj["From"] = os.environ["SMTP_FROM_EMAIL"]
                mesaj["To"] = alici.email
                mesaj["Subject"] = kampanya.subject
                mesaj_domaini = os.environ["SMTP_FROM_EMAIL"].rsplit("@", 1)[-1]
                alici.message_id = alici.message_id or make_msgid(domain=mesaj_domaini)
                mesaj["Message-ID"] = alici.message_id
                if kampanya.reply_to:
                    mesaj["Reply-To"] = kampanya.reply_to
                mesaj.set_content(mesaji_olustur(kampanya.body, alici))
                mesaj.add_alternative(
                    html_mesajini_olustur(kampanya.body, alici), subtype="html"
                )
                try:
                    istemci.send_message(mesaj)
                    alici.status = "SENT"
                    alici.sent_at = datetime.utcnow()
                except Exception as exc:
                    alici.status = "FAILED"
                    alici.error_message = str(exc)[:1000]
                db.commit()
        kampanya.status = (
            "COMPLETED_WITH_ERRORS"
            if any(r.status == "FAILED" for r in kampanya.recipients)
            else "COMPLETED"
        )
        db.commit()
    except Exception:
        kampanya.status = "FAILED"
        db.commit()
    finally:
        db.close()


send_campaign = kampanyayi_gonder
