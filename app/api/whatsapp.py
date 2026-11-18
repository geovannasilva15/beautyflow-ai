"""Opt-in WhatsApp Cloud API pilot with a restricted test inbox."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import requests
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from starlette.concurrency import run_in_threadpool

from app.core.api_access import require_admin
from app.core.time import ensure_utc, utc_now
from app.db.database import TransactionLock, get_session, lock_transaction
from app.db.models import WhatsAppMessage
from app.services.whatsapp_agent_service import detect_intent

webhook = APIRouter(prefix="/whatsapp", tags=["whatsapp"])
inbox = APIRouter(prefix="/whatsapp", tags=["whatsapp"], dependencies=[Depends(require_admin)])
MAX_WEBHOOK_BYTES = 256 * 1024
REPLY_WINDOW = timedelta(hours=23, minutes=45)


@dataclass(frozen=True)
class WhatsAppConfig:
    app_secret: str
    verify_token: str
    access_token: str
    phone_id: str
    business_id: str
    version: str
    recipients: frozenset[str]


def configuration() -> WhatsAppConfig:
    config = WhatsAppConfig(
        app_secret=os.getenv("WHATSAPP_APP_SECRET", "").strip(),
        verify_token=os.getenv("WHATSAPP_VERIFY_TOKEN", "").strip(),
        access_token=os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip(),
        phone_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip(),
        business_id=os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", "").strip(),
        version=os.getenv("WHATSAPP_GRAPH_VERSION", "").strip(),
        recipients=frozenset(filter(None, (item.strip() for item in os.getenv(
            "WHATSAPP_TEST_RECIPIENTS", "",
        ).split(",")))),
    )
    if (
        os.getenv("WHATSAPP_TEST_MODE") != "true"
        or not all((config.app_secret, config.verify_token, config.access_token, config.recipients))
        or not re.fullmatch(r"[0-9]{1,32}", config.phone_id)
        or not re.fullmatch(r"[0-9]{1,32}", config.business_id)
        or not re.fullmatch(r"v[0-9]{1,3}\.[0-9]{1,2}", config.version)
        or any(not re.fullmatch(r"[1-9][0-9]{7,14}", phone) for phone in config.recipients)
    ):
        raise HTTPException(status_code=503, detail="WhatsApp de testes indisponível ou sem configuração.")
    return config


@webhook.get("/webhook", response_class=PlainTextResponse)
def verify_webhook(
    mode: str = Query(alias="hub.mode"),
    token: str = Query(alias="hub.verify_token"),
    challenge: str = Query(alias="hub.challenge", max_length=256),
) -> str:
    config = configuration()
    if mode != "subscribe" or not hmac.compare_digest(token.encode(), config.verify_token.encode()):
        raise HTTPException(status_code=403, detail="Verificação inválida.")
    return challenge


def parse_messages(payload, config: WhatsAppConfig) -> list[WhatsAppMessage]:
    messages = []
    now = utc_now()
    if payload["object"] != "whatsapp_business_account":
        return messages
    for entry in payload.get("entry", []):
        if entry.get("id") != config.business_id:
            continue
        for change in entry.get("changes", []):
            value = change.get("value", {})
            if change.get("field") != "messages" or value.get("metadata", {}).get("phone_number_id") != config.phone_id:
                continue
            for item in value.get("messages", []):
                phone = item.get("from")
                message_id = item.get("id")
                if item.get("type") != "text" or phone not in config.recipients or not isinstance(message_id, str):
                    continue
                body = item.get("text", {}).get("body")
                if not isinstance(body, str) or not body.strip() or not re.fullmatch(r"[A-Za-z0-9_.=+:-]{1,255}", message_id):
                    continue
                received_at = datetime.fromtimestamp(int(item["timestamp"]), tz=timezone.utc)
                if not now - timedelta(hours=24) <= received_at <= now + timedelta(minutes=2):
                    continue
                messages.append(WhatsAppMessage(
                    provider_id=message_id, sender=phone, body=body[:4096], received_at=received_at,
                    intent=detect_intent(body).value,
                ))
    return messages


@webhook.post("/webhook")
async def receive_webhook(request: Request, session: Session = Depends(get_session)) -> dict:
    config = configuration()
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_WEBHOOK_BYTES:
            raise HTTPException(status_code=413, detail="Notificação excede o limite.")
    signature = "sha256=" + hmac.new(config.app_secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(request.headers.get("X-Hub-Signature-256", "").encode(), signature.encode()):
        raise HTTPException(status_code=403, detail="Assinatura inválida.")
    return await run_in_threadpool(store_messages, bytes(body), config, session)


def store_messages(body: bytes, config: WhatsAppConfig, session: Session) -> dict:
    try:
        messages = parse_messages(json.loads(body), config)
    except (ValueError, OverflowError, OSError, TypeError, KeyError, AttributeError) as exc:
        raise HTTPException(status_code=400, detail="Notificação inválida.") from exc
    if messages:
        lock_transaction(session, TransactionLock.WHATSAPP)
        for message in messages:
            if session.get(WhatsAppMessage, message.provider_id) is None:
                session.add(message)
                session.flush()
        session.commit()
    return {"status": "ok"}


@inbox.get("/status")
def whatsapp_status() -> dict:
    try:
        configuration()
    except HTTPException:
        return {"configured": False}
    return {"configured": True, "mode": "test"}


@inbox.get("/inbox")
def list_inbox(session: Session = Depends(get_session)) -> list[WhatsAppMessage]:
    return session.exec(select(WhatsAppMessage).order_by(WhatsAppMessage.received_at.desc()).limit(100)).all()


class ReplyRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4096)
    confirm: bool


@inbox.post("/inbox/{message_id}/reply")
def send_reply(message_id: str, payload: ReplyRequest, session: Session = Depends(get_session)) -> dict:
    config = configuration()
    if not payload.confirm or not payload.text.strip():
        raise HTTPException(status_code=422, detail="Confirme o texto e o destinatário antes de enviar.")
    lock_transaction(session, TransactionLock.WHATSAPP)
    message = session.get(WhatsAppMessage, message_id)
    if not message or message.sender not in config.recipients:
        raise HTTPException(status_code=404, detail="Mensagem de teste não encontrada.")
    if utc_now() - ensure_utc(message.received_at) >= REPLY_WINDOW:
        raise HTTPException(status_code=409, detail="A janela de resposta expirou.")
    if message.reply_status in {"sending", "sent", "unknown"}:
        raise HTTPException(status_code=409, detail="Confira o envio no WhatsApp antes de repetir esta operação.")

    # Claim before contacting Meta. A process failure leaves the result uncertain rather than resending.
    recipient = message.sender
    message.reply_status = "sending"
    message.reply_text = payload.text.strip()
    session.commit()
    try:
        result = requests.post(
            f"https://graph.facebook.com/{config.version}/{config.phone_id}/messages",
            headers={"Authorization": f"Bearer {config.access_token}"},
            json={
                "messaging_product": "whatsapp", "to": recipient, "type": "text",
                "context": {"message_id": message_id},
                "text": {"body": payload.text.strip(), "preview_url": False},
            },
            timeout=(4, 10), allow_redirects=False,
        )
        if result.status_code in {400, 401, 403, 404, 429}:
            message.reply_status = "rejected"
        else:
            result.raise_for_status()
            response_id = result.json()["messages"][0]["id"] if result.ok else None
            if not isinstance(response_id, str) or not 1 <= len(response_id) <= 255 or result.status_code >= 300:
                raise ValueError("Resposta inesperada da Meta")
            message.reply_status = "sent"
            message.reply_provider_id = response_id
    except (requests.RequestException, ValueError, KeyError, TypeError, IndexError):
        message.reply_status = "unknown"
    session.commit()

    if message.reply_status != "sent":
        raise HTTPException(
            status_code=502,
            detail=("A Meta recusou o envio. Confira a configuração de teste."
                    if message.reply_status == "rejected"
                    else "O envio ficou sem confirmação. Confira o WhatsApp antes de reenviar."),
        )
    return {"status": "sent"}
