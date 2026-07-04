"""
Cliente de envio de e-mail via SMTP.

Nota de decisão: nem o cronograma de etapas nem a Seção 2 (Stack)
detalham uma biblioteca específica para envio assíncrono de e-mail (ex:
`aiosmtplib`), mas os fluxos de `AuthService` (confirmação de e-mail,
recuperação de senha) exigem esta integração para serem funcionais de
ponta a ponta. Implemento usando apenas `smtplib` da *standard library*,
executado em thread separada via `asyncio.to_thread` para não bloquear
o event loop — evitando introduzir uma dependência nova não prevista.

Em ambiente de desenvolvimento/teste (sem `SMTP_HOST` configurado), o
cliente **não falha** — ele registra a mensagem via log estruturado e
retorna normalmente, para não travar o fluxo de registro/reset de senha
em ambientes sem infraestrutura de e-mail real.
"""

from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailClient:
    """Fachada de envio de e-mail usada por `AuthService`."""

    def _send_sync(self, *, to: str, subject: str, body: str) -> None:
        assert settings.SMTP_HOST, "SMTP_HOST deve estar configurado para enviar e-mail."
        message = EmailMessage()
        message["From"] = settings.SMTP_FROM_EMAIL
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
            if settings.SMTP_USE_TLS:
                smtp.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD.get_secret_value())
            smtp.send_message(message)

    async def send_email(self, *, to: str, subject: str, body: str) -> None:
        """Envia um e-mail de forma assíncrona (via thread), sem bloquear o event loop."""
        if not settings.SMTP_HOST:
            logger.warning(
                "smtp_not_configured_email_skipped",
                to=to,
                subject=subject,
            )
            return
        await asyncio.to_thread(self._send_sync, to=to, subject=subject, body=body)

    async def send_email_confirmation(self, *, to: str, token: str) -> None:
        """Envia o e-mail com o token de confirmação de cadastro (Seção 6)."""
        body = (
            "Bem-vindo(a)! Confirme seu cadastro usando o token abaixo no endpoint "
            f"de confirmação de e-mail:\n\n{token}\n\n"
            f"Este token expira em {settings.EMAIL_TOKEN_EXPIRE_HOURS} horas."
        )
        await self.send_email(to=to, subject="Confirme seu e-mail", body=body)

    async def send_password_reset(self, *, to: str, token: str) -> None:
        """Envia o e-mail com o token de redefinição de senha (Seção 6: `/auth/password/reset`)."""
        body = (
            "Recebemos uma solicitação de redefinição de senha. Use o token abaixo "
            f"no endpoint de redefinição:\n\n{token}\n\n"
            f"Este token expira em {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutos. "
            "Se você não solicitou isso, ignore este e-mail."
        )
        await self.send_email(to=to, subject="Redefinição de senha", body=body)
