"""
Gerencia o fluxo de OAuth2 Authorization Code para login social.

Como a especificação não detalha os provedores (Google, GitHub, etc.), criei
uma estrutura genérica. Novos provedores entram em `app/integrations/oauth_providers/`
apenas como configuração, sem repetir código.

Reaproveitei o `httpx` (indicado para testes) para fazer as chamadas HTTP de
troca de código e perfil, evitando instalar novas bibliotecas (como authlib).
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from urllib.parse import urlencode

import httpx


class OAuth2ExchangeError(Exception):
    """Erro lançado quando o provedor falha em trocar o authorization_code pelo token."""


@dataclass(frozen=True, slots=True)
class OAuth2ProviderConfig:
    """
    Configuração de um provedor OAuth2 externo.

    As instâncias (como Google ou GitHub) são criadas dinamicamente com
    base nas variáveis de ambiente. Este gerenciador não possui nomes de
    provedores fixos no código.
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
    """Interface para o fluxo Authorization Code, independente do provedor usado."""

    @staticmethod
    def generate_state() -> str:
        """
        Gera um token `state` seguro contra ataques CSRF no fluxo OAuth2.

        O `auth_service` deve salvar e validar esse token (ex: no Redis com TTL curto).
        Este método apenas gera o valor.
        """

        return secrets.token_urlsafe(32)

    @staticmethod
    def build_authorization_url(config: OAuth2ProviderConfig, *, state: str) -> str:
        """Cria a URL de redirecionamento para a tela de login/consentimento do provedor."""

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
        Troca o `authorization_code` do callback pelo access token do provedor.

        Qualquer erro de rede ou resposta inválida gera um `OAuth2ExchangeError`.
        Exceções do `httpx` nunca são propagadas direto para os services.
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
        """Busca as informações básicas do usuário (e-mail, nome) no provedor externo."""
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
