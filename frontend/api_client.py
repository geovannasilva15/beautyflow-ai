from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlsplit

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


class BeautyFlowAPIError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def get_api_url() -> str:
    url = os.getenv("API_URL", "http://127.0.0.1:8000/api").rstrip("/")
    if os.getenv("APP_ENV", "development").strip().lower() == "production" and urlsplit(url).scheme != "https":
        raise BeautyFlowAPIError("Configure uma API com HTTPS.")
    return url


def _request(method: str, path: str, **kwargs) -> Any:
    token = st.session_state.get("access_token")
    headers = {"Authorization": f"Bearer {token}"} if token and path != "/auth/login" else {}
    try:
        response = requests.request(
            method, f"{get_api_url()}{path}", timeout=(5, 35), headers=headers,
            allow_redirects=False, **kwargs,
        )
    except requests.RequestException as exc:
        raise BeautyFlowAPIError("API indisponível. Tente novamente em instantes.") from exc
    if not 200 <= response.status_code < 300:
        try:
            detail = response.json().get("detail")
        except (ValueError, AttributeError):
            detail = None
        if isinstance(detail, list):
            detail = "Verifique os campos e os limites indicados no formulário."
        raise BeautyFlowAPIError(detail or "Não foi possível concluir a operação.", response.status_code)
    return None if response.status_code == 204 else response.json()


def api_get(path: str, params: dict | None = None) -> Any:
    return _request("GET", path, params=params)


def api_post(path: str, json: dict | None = None, params: dict | None = None) -> Any:
    return _request("POST", path, json=json, params=params)


def api_put(path: str, json: dict | None = None) -> Any:
    return _request("PUT", path, json=json)


def api_patch(path: str, json: dict | None = None) -> Any:
    return _request("PATCH", path, json=json)


def api_delete(path: str) -> Any:
    return _request("DELETE", path)


def format_currency(value: float | int | None) -> str:
    value = float(value or 0)
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
