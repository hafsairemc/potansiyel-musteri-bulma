import imaplib
import os
from dataclasses import dataclass
from datetime import datetime
from email import policy
from email.message import Message
from email.parser import BytesParser

from models.growth_model import EmailCampaign, EmailRecipient


class EpostaYanitHatasi(RuntimeError):
    pass


EmailReplyError = EpostaYanitHatasi


@dataclass(frozen=True)
class EpostaSenkronSonucu:
    replies: int = 0
    bounces: int = 0


EmailSyncResult = EpostaSenkronSonucu

GERI_DONUS_TERIMLERI = (
    "delivery status notification",
    "delivery failure",
    "mail delivery failed",
    "returned mail",
    "undeliverable",
    "ileti teslim edilemedi",
)
BOUNCE_TERMS = GERI_DONUS_TERIMLERI


class EpostaYanitServisi:
    BOUNCE_TERMS = GERI_DONUS_TERIMLERI

    def yapilandirilmis_mi(self) -> bool:
        gerekli = ("IMAP_HOST", "IMAP_USERNAME", "IMAP_PASSWORD")
        return all(os.getenv(isim) for isim in gerekli)

    configured = yapilandirilmis_mi

    def senkronize_et(
        self,
        campaign: EmailCampaign,
        recipients_list: list[EmailRecipient],
    ) -> EpostaSenkronSonucu:
        if not self.yapilandirilmis_mi():
            raise EpostaYanitHatasi(
                "Yanıt kontrolü için IMAP bilgileri yapılandırılmamış"
            )
        alicilar = {
            oge.message_id: oge for oge in recipients_list if oge.message_id
        }
        if not alicilar:
            return EpostaSenkronSonucu()

        istemci_sinifi = imaplib.IMAP4_SSL if self._ssl_kullanilsin_mi() else imaplib.IMAP4
        try:
            with istemci_sinifi(
                os.environ["IMAP_HOST"],
                int(os.getenv("IMAP_PORT", "993")),
            ) as istemci:
                istemci.login(
                    os.environ["IMAP_USERNAME"],
                    os.environ["IMAP_PASSWORD"],
                )
                istemci.select(os.getenv("IMAP_FOLDER", "INBOX"), readonly=True)
                baslangic = (campaign.approved_at or campaign.created_at).strftime(
                    "%d-%b-%Y"
                )
                durum, veri = istemci.search(None, "SINCE", baslangic)
                if durum != "OK":
                    raise EpostaYanitHatasi("Posta kutusu aranamadı")
                return self._mesajlari_oku(istemci, veri[0].split(), alicilar)
        except EpostaYanitHatasi:
            raise
        except (imaplib.IMAP4.error, OSError, ValueError) as exc:
            raise EpostaYanitHatasi("Posta kutusuna bağlanılamadı") from exc

    sync = senkronize_et

    def _mesajlari_oku(
        self,
        client,
        message_numbers: list[bytes],
        recipients: dict[str, EmailRecipient],
    ) -> EpostaSenkronSonucu:
        yanitlar = 0
        sekenler = 0
        for numara in message_numbers[-500:]:
            mesaj = self._mesaji_cek(client, numara, headers_only=True)
            if mesaj is None:
                continue
            if self.geri_donus_adayi_mi(mesaj):
                tam_mesaj = self._mesaji_cek(client, numara, headers_only=False)
                alici = self.geri_donus_alici_esle(tam_mesaj, recipients)
                if alici:
                    sekenler += int(self.geri_donus_uygula(alici, tam_mesaj))
                continue
            alici = self.alici_esle(mesaj, recipients)
            if not alici:
                continue
            yeni_yanit_mi = alici.replied_at is None
            alici.replied_at = alici.replied_at or datetime.now()
            alici.reply_subject = str(mesaj.get("Subject") or "")[:500]
            alici.reply_from = str(mesaj.get("From") or "")[:255]
            yanitlar += int(yeni_yanit_mi)
        return EpostaSenkronSonucu(replies=yanitlar, bounces=sekenler)

    _read_messages = _mesajlari_oku

    @staticmethod
    def _mesaji_cek(client, number: bytes, headers_only: bool) -> Message | None:
        sorgu = (
            "(BODY.PEEK[HEADER.FIELDS "
            "(IN-REPLY-TO REFERENCES FROM DATE SUBJECT CONTENT-TYPE "
            "AUTO-SUBMITTED X-FAILED-RECIPIENTS)])"
            if headers_only
            else "(BODY.PEEK[])"
        )
        durum, parcalar = client.fetch(number, sorgu)
        if durum != "OK":
            return None
        ham = next((parca[1] for parca in parcalar if isinstance(parca, tuple)), None)
        if not ham:
            return None
        return BytesParser(policy=policy.default).parsebytes(ham)

    _fetch_message = _mesaji_cek

    @classmethod
    def geri_donus_adayi_mi(cls, message: Message) -> bool:
        icerik_turu = message.get_content_type().lower()
        rapor_turu = str(message.get_param("report-type") or "").lower()
        gonderen = str(message.get("From") or "").lower()
        konu = str(message.get("Subject") or "").lower()
        return bool(
            message.get("X-Failed-Recipients")
            or rapor_turu == "delivery-status"
            or icerik_turu == "message/delivery-status"
            or "mailer-daemon" in gonderen
            or "postmaster" in gonderen
            or any(terim in konu for terim in cls.BOUNCE_TERMS)
        )

    is_bounce_candidate = geri_donus_adayi_mi

    @classmethod
    def geri_donus_alici_esle(
        cls,
        message: Message | None,
        recipients: dict[str, EmailRecipient],
    ) -> EmailRecipient | None:
        if message is None:
            return None
        kanit = cls._mesaj_kaniti(message)
        return next(
            (
                alici
                for mesaj_id, alici in recipients.items()
                if mesaj_id and mesaj_id in kanit
            ),
            None,
        )

    match_bounce_recipient = geri_donus_alici_esle

    @classmethod
    def geri_donus_uygula(
        cls,
        recipient: EmailRecipient,
        message: Message | None,
    ) -> bool:
        yeni_mi = recipient.bounced_at is None
        recipient.bounced_at = recipient.bounced_at or datetime.now()
        recipient.delivery_status = "BOUNCED"
        recipient.status = "FAILED"
        recipient.bounce_reason = cls._geri_donus_sebebi(message)
        return yeni_mi

    apply_bounce = geri_donus_uygula

    @classmethod
    def _mesaj_kaniti(cls, message: Message) -> str:
        degerler: list[str] = []
        cls._mesaj_degerlerini_topla(message, degerler)
        return " ".join(degerler)

    _message_evidence = _mesaj_kaniti

    @classmethod
    def _mesaj_degerlerini_topla(cls, message: Message, values: list[str]) -> None:
        values.extend(str(deger) for _, deger in message.raw_items())
        yuk = message.get_payload()
        if isinstance(yuk, list):
            for parca in yuk:
                if isinstance(parca, Message):
                    cls._mesaj_degerlerini_topla(parca, values)

    _collect_message_values = _mesaj_degerlerini_topla

    @classmethod
    def _geri_donus_sebebi(cls, message: Message | None) -> str | None:
        if message is None:
            return None
        degerler: list[str] = []
        cls._baslik_topla(message, "Diagnostic-Code", degerler)
        cls._baslik_topla(message, "Status", degerler)
        if not degerler:
            konu = str(message.get("Subject") or "").strip()
            return konu[:500] or None
        return " · ".join(dict.fromkeys(degerler))[:500]

    _bounce_reason = _geri_donus_sebebi

    @classmethod
    def _baslik_topla(
        cls,
        message: Message,
        header: str,
        values: list[str],
    ) -> None:
        deger = str(message.get(header) or "").strip()
        if deger:
            values.append(deger)
        yuk = message.get_payload()
        if isinstance(yuk, list):
            for parca in yuk:
                if isinstance(parca, Message):
                    cls._baslik_topla(parca, header, values)

    _collect_header = _baslik_topla

    @staticmethod
    def alici_esle(
        message: Message,
        recipients: dict[str, EmailRecipient],
    ) -> EmailRecipient | None:
        referanslar = f"{message.get('In-Reply-To', '')} {message.get('References', '')}"
        return next(
            (
                alici
                for mesaj_id, alici in recipients.items()
                if mesaj_id in referanslar
            ),
            None,
        )

    match_recipient = alici_esle

    @staticmethod
    def _ssl_kullanilsin_mi() -> bool:
        return os.getenv("IMAP_USE_SSL", "true").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    _use_ssl = _ssl_kullanilsin_mi


EmailReplyService = EpostaYanitServisi
