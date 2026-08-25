import os
from datetime import datetime, timedelta
import jwt

from core.config import settings

JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"


def erisim_jetonu_olustur(user_data: dict) -> str:
    """Yalnızca yerel geliştirme ve test oturumları için kullanılır."""
    if not settings.dev_mode or not JWT_SECRET:
        raise RuntimeError("Yerel JWT yalnız DEV_MODE ve JWT_SECRET ile kullanılabilir.")

    yuk = user_data.copy()
    yuk["exp"] = datetime.utcnow() + timedelta(hours=24)
    return jwt.encode(yuk, JWT_SECRET, algorithm=JWT_ALGORITHM)


create_access_token = erisim_jetonu_olustur
