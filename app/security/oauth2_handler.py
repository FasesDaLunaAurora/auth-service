"""
Handler de domínio para o fluxo OAuth2 Authorization Code (login social).

Nota de decisão: a Seção 6 (contrato de endpoints) não define nenhuma
rota `/auth/oauth/*` concreta, apenas a tabela da Seção 3 menciona
"OAuth2" como responsabilidade da camada `security`. Sem um provider
específico (Google, GitHub, etc.) definido na especificação, implemento
aqui uma abstração **genérica e reutilizável** do fluxo Authorization
Code (RFC 6749) — cada provider concreto (quando necessário) vira uma
pequena configuração em `app/integrations/oauth_providers/`, sem
duplicar a lógica de troca de código por token.

Uso de `httpx`: a especificação lista `httpx` apenas na categoria
"Testes" (Seção 2). Reaproveito a mesma biblioteca aqui para as
chamadas HTTP ao provider OAuth (troca de código, userinfo) em vez de
introduzir uma dependência nova (ex: `authlib`) — é uma extensão do uso
de uma lib já aprovada, não uma substituição de tecnologia da Seção 2.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from urllib.parse import urlencode

import httpx


class OAuth2ExchangeError(Exception):
    """Levantada quando a troca do `authorization_code` pelo token falha no provider."""


@dataclass(frozen=True, slots=True)
class OAuth2ProviderConfig:
    """
    Configuração de um provider OAuth2 externo.

    Instâncias concretas (ex: Google, GitHub) são construídas em
    `app/integrations/oauth_providers/` a partir de variáveis de
    ambiente específicas do provider — este handler não conhece
    nenhum provider por nome.
    """

    name: str
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    redirect_uri: str
    scopes: list[str] = field(default_factory=list)


class OAuth2Handler:
    """Fachada de fluxo Authorization Code, agnóstica de provider específico."""

    @staticmethod
    def generate_state() -> str:
        """
        Gera um valor `state` (CSRF token do fluxo OAuth2) criptograficamente
        seguro. O chamador (`auth_service`) é responsável por persistir/
        comparar este valor (ex: em Redis com TTL curto) para validar o
        callback — este handler apenas gera o valor.
        """
        return secrets.token_urlsafe(32)

    @staticmethod
    def build_authorization_url(config: OAuth2ProviderConfig, *, state: str) -> str:
        """Monta a URL de redirecionamento para a tela de consentimento do provider."""
        params = {
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(config.scopes),
            "state": state,
        }
        return f"{config.authorize_url}?{urlencode(params)}"

    @staticmethod
    async def exchange_code_for_token(config: OAuth2ProviderConfig, *, code: str) -> dict[str, str]:
        """
        Troca o `authorization_code` recebido no callback por um access
        token do provider externo.

        Erros de rede ou resposta não-2xx são traduzidos para
        `OAuth2ExchangeError` — este handler nunca propaga exceções de
        `httpx` diretamente para a camada de `services`.
        """
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config.redirect_uri,
            "client_id": config.client_id,
            "client_secret": config.client_secret,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    config.token_url,
                    data=payload,
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                return dict(response.json())
        except httpx.HTTPError as exc:
            raise OAuth2ExchangeError(
                f"Falha ao trocar código de autorização com o provider '{config.name}'."
            ) from exc

    @staticmethod
    async def fetch_user_info(config: OAuth2ProviderConfig, *, access_token: str) -> dict[str, str]:
        """Busca as informações básicas do usuário (e-mail, nome) no provider externo."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    config.userinfo_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
                return dict(response.json())
        except httpx.HTTPError as exc:
            raise OAuth2ExchangeError(
                f"Falha ao buscar informações do usuário no provider '{config.name}'."
            ) from exc
