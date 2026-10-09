from __future__ import annotations

from app.services import ai_service


def test_ai_endpoint_missing_key_returns_503(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = client.post("/api/ai/chat", json={"question": "Como melhorar agenda?", "business_context": "Salão"})
    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]


def test_ai_endpoint_calls_provider(client, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"choices": [{"message": {"content": "Use lembretes de agendamento."}}]}
    def fake_post(url, **kwargs):
        assert url == "https://api.openai.com/v1/chat/completions"
        assert kwargs["headers"]["Authorization"] == "Bearer test-key"
        return Response()
    monkeypatch.setattr(ai_service.requests, "post", fake_post)
    response = client.post("/api/ai/chat", json={"question": "Como reduzir faltas?", "business_context": "Salão"})
    assert response.status_code == 200
    assert response.json()["answer"] == "Use lembretes de agendamento."
