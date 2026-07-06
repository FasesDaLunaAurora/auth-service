"""
Cliente de envio de e-mails via SMTP.

Usa a biblioteca nativa `smtplib` rodando em uma thread separada via
`asyncio.to_thread` para não travar o event loop da aplicação, evitando
dependências externas desnecessárias.

Se o `SMTP_HOST` não estiver configurado (ambiente local/testes), o cliente
apenas printa o e-mail no log estruturado e simula o sucesso do envio,
evitando quebrar o fluxo de onboarding nas máquinas locais.
"""

from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailClient:
    """Helper de envio de e-mails para o `AuthService`."""

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
        """Envia o e-mail em background sem travar o event loop."""
        if not settings.SMTP_HOST:
            logger.warning(
                "smtp_not_configured_email_skipped",
                to=to,
                subject=subject,
            )
            return
        await asyncio.to_thread(self._send_sync, to=to, subject=subject, body=body)

    async def send_email_confirmation(self, *, to: str, token: str) -> None:
        """Envia o e-mail com o token de confirmação de cadastro."""
        body = (
            "Bem-vindo(a)! Confirme seu cadastro usando o token abaixo no endpoint "
            f"de confirmação de e-mail:\n\n{token}\n\n"
            f"Este token expira em {settings.EMAIL_TOKEN_EXPIRE_HOURS} horas."
        )
        await self.send_email(to=to, subject="Confirme seu e-mail", body=body)

    async def send_password_reset(self, *, to: str, token: str) -> None:
        """Envia o e-mail com o token de redefinição de senha."""
        body = (
            "Recebemos uma solicitação de redefinição de senha. Use o token abaixo "
            f"no endpoint de redefinição:\n\n{token}\n\n"
            f"Este token expira em {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutos. "
            "Se você não solicitou isso, ignore este e-mail."
        )
        await self.send_email(to=to, subject="Redefinição de senha", body=body)
