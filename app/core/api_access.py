from __future__ import annotations

import hmac
import os
from fastapi import HTTPException, Request


def require_api_key(request: Request) -> None:
    """Single-application access guard, not a replacement for multiuser auth."""
    expected = os.getenv("API_ACCESS_TOKEN", "")
    if not expected:
        if os.getenv("APP_ENV", "development").lower() == "production":
            raise HTTPException(status_code=503, detail="API_ACCESS_TOKEN não configurado.")
        return
    if not hmac.compare_digest(request.headers.get("X-API-Key", ""), expected):
        raise HTTPException(status_code=401, detail="Credencial da API inválida.")
