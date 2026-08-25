import os
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

dakikalik_limit = os.getenv("API_RATE_LIMIT_PER_MINUTE", "60")
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{dakikalik_limit}/minute"],
)


def hiz_sinirlayici_ekle(app):
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


sinirlayici = limiter
add_rate_limiter_to_app = hiz_sinirlayici_ekle
