import hashlib
import hmac
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.growth_model import EmailDeliveryEvent, EmailRecipient
from schemas.growth_schema import EmailDeliveryEventBody


class EpostaOlayHatasi(ValueError):
    pass


EmailEventError = EpostaOlayHatasi


def imza_gecerli_mi(body: bytes, signature: str, secret: str) -> bool:
    if not signature or not secret:
        return False
    iletilen = signature.removeprefix("sha256=").strip().lower()
    beklenen = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(iletilen, beklenen)


valid_signature = imza_gecerli_mi


class EpostaOlayServisi:
    async def olayi_isle(
        self,
        db: AsyncSession,
        event: EmailDeliveryEventBody,
    ) -> str:
        mevcut = (
            await db.execute(
                select(EmailDeliveryEvent.id).where(
                    EmailDeliveryEvent.provider == event.provider.lower(),
                    EmailDeliveryEvent.event_id == event.event_id,
                )
            )
        ).scalar_one_or_none()
        if mevcut:
            return "duplicate"

        alici = (
            await db.execute(
                select(EmailRecipient).where(
                    EmailRecipient.message_id == event.message_id
                )
            )
        ).scalar_one_or_none()
        if alici is None:
            raise EpostaOlayHatasi("E-posta alıcısı bulunamadı")

        olay_zamani = event.occurred_at or datetime.now()
        self._aliciyi_guncelle(alici, event, olay_zamani)
        db.add(
            EmailDeliveryEvent(
                recipient_id=alici.id,
                provider=event.provider.lower(),
                event_id=event.event_id,
                event_type=event.event_type,
                occurred_at=olay_zamani,
                reason=event.reason,
            )
        )
        await db.commit()
        return "accepted"

    apply = olayi_isle

    @staticmethod
    def _aliciyi_guncelle(
        recipient: EmailRecipient,
        event: EmailDeliveryEventBody,
        occurred_at: datetime,
    ) -> None:
        recipient.delivery_status = event.event_type.upper()
        if event.event_type == "delivered":
            recipient.delivered_at = recipient.delivered_at or occurred_at
        elif event.event_type == "bounced":
            recipient.bounced_at = recipient.bounced_at or occurred_at
            recipient.bounce_reason = event.reason
            recipient.status = "FAILED"
        else:
            recipient.complained_at = recipient.complained_at or occurred_at
            recipient.status = "COMPLAINED"

    _update_recipient = _aliciyi_guncelle


EmailEventService = EpostaOlayServisi
