"""
Testes unitários do `OAuth2Handler`.

Valida a estrutura genérica do fluxo Authorization Code. Como os provedores
reais ainda não foram configurados, os testes usam dados fictícios e simulam
as chamadas HTTP (mock) para não depender de nenhum serviço externo.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.security.oauth2_handler import (
    OAuth2ExchangeError,
    OAuth2Handler,
    OAuth2ProviderConfig,
)

_FAKE_PROVIDER = OAuth2ProviderConfig(
    name="fake-provider",
    client_id="fake-client-id",
    client_secret="fake-client-secret",
    authorize_url="https://fake-provider.example.com/authorize",
    token_url="https://fake-provider.example.com/token",
    userinfo_url="https://fake-provider.example.com/userinfo",
    redirect_uri="https://auth-service.example.com/callback",
    scopes=["openid", "email"],
)


def test_generate_state_returns_a_url_safe_random_token() -> None:
    state = OAuth2Handler.generate_state()
    assert len(state) > 20
    assert " " not in state


def test_generate_state_is_different_each_call() -> None:
    assert OAuth2Handler.generate_state() != OAuth2Handler.generate_state()


def test_build_authorization_url_includes_all_required_query_params() -> None:
    url = OAuth2Handler.build_authorization_url(_FAKE_PROVIDER, state="fixed-state-value")

    assert url.startswith(_FAKE_PROVIDER.authorize_url)
    assert "client_id=fake-client-id" in url
    assert "response_type=code" in url
    assert "state=fixed-state-value" in url
    assert "scope=openid+email" in url or "scope=openid%20email" in url


@pytest.mark.asyncio
async def test_exchange_code_for_token_returns_parsed_json_on_success() -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = {"access_token": "fake-token", "token_type": "bearer"}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await OAuth2Handler.exchange_code_for_token(_FAKE_PROVIDER, code="fake-code")

    assert result == {"access_token": "fake-token", "token_type": "bearer"}


@pytest.mark.asyncio
async def test_exchange_code_for_token_raises_domain_error_on_http_failure() -> None:
    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.ConnectError("connection failed")
    mock_client.__aenter__.return_value = mock_client

    with patch("httpx.AsyncClient", return_value=mock_client), pytest.raises(OAuth2ExchangeError):
        await OAuth2Handler.exchange_code_for_token(_FAKE_PROVIDER, code="fake-code")


@pytest.mark.asyncio
async def test_fetch_user_info_returns_parsed_json_on_success() -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = {"email": "user@example.com", "name": "Fake User"}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await OAuth2Handler.fetch_user_info(_FAKE_PROVIDER, access_token="fake-token")

    assert result["email"] == "user@example.com"


@pytest.mark.asyncio
async def test_fetch_user_info_raises_domain_error_on_http_failure() -> None:
    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.ConnectError("connection failed")
    mock_client.__aenter__.return_value = mock_client

    with patch("httpx.AsyncClient", return_value=mock_client), pytest.raises(OAuth2ExchangeError):
        await OAuth2Handler.fetch_user_info(_FAKE_PROVIDER, access_token="fake-token")
