from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st


class BeautyFlowAPIError(RuntimeError):
    pass


def get_api_url() -> str:
    try:
        api_url = st.secrets.get("API_URL")
        if api_url:
            return str(api_url).rstrip("/")
    except Exception:
        pass
    return os.getenv("API_URL", "http://127.0.0.1:8000/api").rstrip("/")


API_URL = get_api_url()


def _headers() -> dict[str, str]:
    try:
        token = st.secrets.get('API_ACCESS_TOKEN') or os.getenv('API_ACCESS_TOKEN', '')
    except Exception:
        token = os.getenv('API_ACCESS_TOKEN', '')
    return {'X-API-Key': str(token)} if token else {}


def _handle_response(response: requests.Response) -> Any:
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        try:
            payload = response.json()
            detail = payload.get("detail") or payload.get("message")
        except Exception:
            detail = None
        raise BeautyFlowAPIError(detail or "Não foi possível concluir a operação.") from exc

    if response.status_code == 204:
        return None
    return response.json()


def api_get(path: str, params: dict | None = None) -> Any:
    response = requests.get(f"{API_URL}{path}", params=params, timeout=20, headers=_headers())
    return _handle_response(response)


def api_post(path: str, json: dict | None = None, params: dict | None = None) -> Any:
    response = requests.post(f"{API_URL}{path}", json=json, params=params, timeout=60, headers=_headers())
    return _handle_response(response)


def api_put(path: str, json: dict | None = None) -> Any:
    response = requests.put(f"{API_URL}{path}", json=json, timeout=60, headers=_headers())
    return _handle_response(response)


def api_patch(path: str, json: dict | None = None) -> Any:
    response = requests.patch(f"{API_URL}{path}", json=json, timeout=60, headers=_headers())
    return _handle_response(response)


def api_delete(path: str) -> Any:
    response = requests.delete(f"{API_URL}{path}", timeout=60, headers=_headers())
    return _handle_response(response)


def api_online() -> bool:
    try:
        api_get("/health")
        return True
    except Exception:
        return False


def format_currency(value: float | int | None) -> str:
    value = float(value or 0)
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
