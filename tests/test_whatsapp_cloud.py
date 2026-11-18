import hashlib
import hmac
import json
from datetime import timedelta

import pytest
import requests

from app.api import whatsapp
from app.core.time import utc_now


@pytest.fixture
def whatsapp_test_config(monkeypatch):
    for key, value in {
        "WHATSAPP_TEST_MODE": "true",
        "WHATSAPP_APP_SECRET": "fake-app-secret",
        "WHATSAPP_VERIFY_TOKEN": "fake-verification",
        "WHATSAPP_ACCESS_TOKEN": "fake-api-token",
        "WHATSAPP_PHONE_NUMBER_ID": "1234",
        "WHATSAPP_BUSINESS_ACCOUNT_ID": "2222",
        "WHATSAPP_GRAPH_VERSION": "v25.0",
        "WHATSAPP_TEST_RECIPIENTS": "5511999999999",
    }.items():
        monkeypatch.setenv(key, value)


def record(api, *, sender="5511999999999", message_id="wamid.test", timestamp=None, signature_valid=True, business_id="2222"):
    body = json.dumps({
        "object": "whatsapp_business_account",
        "entry": [{"id": business_id, "changes": [{"field": "messages", "value": {
            "metadata": {"phone_number_id": "1234"},
            "messages": [{
                "id": message_id, "from": sender, "timestamp": str(int((timestamp or utc_now()).timestamp())),
                "type": "text", "text": {"body": "Gostaria de agendar."},
            }],
        }}]}],
    }).encode()
    signature = hmac.new(b"fake-app-secret", body, hashlib.sha256).hexdigest() if signature_valid else "invalid"
    return api.post("/api/whatsapp/webhook", content=body, headers={"X-Hub-Signature-256": "sha256=" + signature})


def test_cloud_webhook_verification_dedupe_and_allowlist(client, monkeypatch, whatsapp_test_config):
    verify = {"hub.mode": "subscribe", "hub.verify_token": "fake-verification", "hub.challenge": "100"}
    response = client.get("/api/whatsapp/webhook", params=verify)
    assert response.status_code == 200 and response.text == "100"
    assert client.get("/api/whatsapp/webhook", params={**verify, "hub.verify_token": "wrong"}).status_code == 403
    assert record(client, signature_valid=False).status_code == 403
    assert record(client, sender="5511988888888", message_id="wrong-sender").status_code == 200
    assert record(client, business_id="9999", message_id="wrong-account").status_code == 200
    assert record(client).status_code == 200
    assert record(client).status_code == 200
    messages = client.get("/api/whatsapp/inbox").json()
    assert len(messages) == 1
    assert messages[0]["intent"] == "agendar"
    assert client.get("/api/appointments").json() == []
    monkeypatch.delenv("WHATSAPP_ACCESS_TOKEN")
    assert client.get("/api/whatsapp/status").json() == {"configured": False}
    assert record(client).status_code == 503


def test_confirmed_test_reply_and_uncertain_delivery(client, monkeypatch, whatsapp_test_config):
    assert record(client).status_code == 200
    assert record(client, message_id="wamid.old", timestamp=utc_now() - timedelta(hours=23, minutes=50)).status_code == 200
    calls = []

    def fake_post(url, **kwargs):
        calls.append(kwargs)
        assert url == "https://graph.facebook.com/v25.0/1234/messages"
        assert kwargs["headers"]["Authorization"] == "Bearer fake-api-token"
        assert kwargs["json"]["to"] == "5511999999999"
        response = requests.Response()
        response.status_code = 200
        response._content = b'{"messages":[{"id":"wamid.reply"}]}'
        return response

    monkeypatch.setattr(whatsapp.requests, "post", fake_post)
    endpoint = "/api/whatsapp/inbox/wamid.test/reply"
    assert client.post(endpoint, json={"text": "Olá!", "confirm": False}).status_code == 422
    assert client.post("/api/whatsapp/inbox/wamid.old/reply", json={"text": "Olá!", "confirm": True}).status_code == 409
    assert not calls
    assert client.post(endpoint, json={"text": "Olá!", "confirm": True}).status_code == 200
    assert client.post(endpoint, json={"text": "Olá!", "confirm": True}).status_code == 409
    assert len(calls) == 1

    assert record(client, message_id="wamid.timeout").status_code == 200

    def timeout(*args, **kwargs):
        raise requests.Timeout()

    monkeypatch.setattr(whatsapp.requests, "post", timeout)
    endpoint = "/api/whatsapp/inbox/wamid.timeout/reply"
    assert client.post(endpoint, json={"text": "Olá!", "confirm": True}).status_code == 502
    assert client.post(endpoint, json={"text": "Olá!", "confirm": True}).status_code == 409
    assert client.get("/api/whatsapp/inbox").json()[0]["reply_status"] == "unknown"
