from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.api.auth import router as auth_router
from app.api.routes import router
from app.api.whatsapp import inbox, webhook
from app.core.api_access import current_account
from app.core.config import get_settings
from app.db.database import engine, get_session

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if os.getenv("APP_ENV", "development").strip().lower() == "production":
        if engine.dialect.name != "postgresql":
            raise RuntimeError("Produção exige PostgreSQL.")
    yield


app = FastAPI(title=settings.app_name, version="2.0.0", lifespan=lifespan)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(webhook, prefix=settings.api_prefix)
app.include_router(inbox, prefix=settings.api_prefix)
app.include_router(router, prefix=settings.api_prefix, dependencies=[Depends(current_account)])


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    # Pydantic includes the submitted value in many errors. Never echo it.
    fields = [
        {"loc": error["loc"], "msg": error["msg"], "type": error["type"]}
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": fields})


@app.get("/healthz", include_in_schema=False)
@app.get(settings.api_prefix + "/health")
def deployment_health(session: Session = Depends(get_session)) -> dict[str, str]:
    try:
        session.execute(text("SELECT id FROM account LIMIT 1"))
        session.execute(text("SELECT duration_minutes FROM appointment LIMIT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Banco indisponível ou migrações pendentes.") from exc
    return {"status": "ok", "timezone": settings.business_timezone}
