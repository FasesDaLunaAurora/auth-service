"""
Regras de negócio de autenticação: registro, login, MFA, rotação de
refresh token, logout e recuperação de senha (Seção 7).

Regra de camada (Seção 3): este módulo nunca importa `Request`,
`Response` ou `HTTPException` — ele só levanta exceções de
`app/exceptions/`, traduzidas para HTTP exclusivamente por
`exception_handlers.py` na camada de API.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from app.core.config import settings
from app.core.constants import TokenType
from app.core.security import utcnow
from app.exceptions.auth_exceptions import (
    AccountInactiveError,
    AccountLockedError,
    AccountNotVerifiedError,
    InvalidCredentialsError,
    InvalidMFACodeError,
    InvalidTokenError,
    TokenRevokedError,
)
from app.exceptions.user_exceptions import EmailAlreadyExistsError
from app.integrations.email_client import EmailClient
from app.models.refresh_token_model import RefreshToken
from app.models.session_model import Session
from app.models.user_model import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth_schema import (
    ConfirmEmailRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    VerifyMFARequest,
)
from app.schemas.token_schema import MFAChallengeResponse, TokenResponse
from app.security.jwt_handler import JWTHandler
from app.security.mfa_handler import MFAHandler
from app.security.password_handler import PasswordHandler

# Hash "descartável" usado para manter o tempo de resposta de login
# constante quando o e-mail informado não existe — mitiga enumeration
# attacks por análise de timing (Seção 8), calculado uma única vez.
_DUMMY_PASSWORD_HASH = PasswordHandler.hash("timing-attack-mitigation-placeholder")


class AuthService:
    """Orquestra os fluxos de autenticação descritos na Seção 7 da especificação."""

    def __init__(
        self,
        user_repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository,
        session_repository: SessionRepository,
        email_client: EmailClient,
    ) -> None:
        self._users = user_repository
        self._refresh_tokens = refresh_token_repository
        self._sessions = session_repository
        self._email_client = email_client

    # --- Registro ---

    async def register(self, payload: RegisterRequest) -> User:
        """Cadastra um novo usuário e dispara o e-mail de confirmação."""
        if await self._users.exists_by_email(payload.email):
            raise EmailAlreadyExistsError()

        user = User(
            email=payload.email,
            full_name=payload.full_name,
            hashed_password=PasswordHandler.hash(payload.password),
        )
        await self._users.create(user)

        confirmation = JWTHandler.create_email_confirmation_token(user.id)
        await self._email_client.send_email_confirmation(to=user.email, token=confirmation.token)
        return user

    # --- Login / MFA ---

    async def login(
        self, payload: LoginRequest, *, ip_address: str, device_info: str | None
    ) -> TokenResponse | MFAChallengeResponse:
        """
        Executa o fluxo de login da Seção 7.

        Retorna `TokenResponse` diretamente se a conta não tiver MFA
        ativo, ou `MFAChallengeResponse` se um segundo fator for
        necessário para concluir o login.
        """
        user = await self._users.get_by_email(payload.email)

        if user is None:
            # Executa uma verificação de senha "descartável" mesmo sem
            # usuário encontrado, para que o tempo de resposta não
            # revele se o e-mail existe (Seção 8).
            PasswordHandler.verify(payload.password, _DUMMY_PASSWORD_HASH)
            raise InvalidCredentialsError()

        if user.is_locked:
            raise AccountLockedError()

        is_valid, new_hash = PasswordHandler.verify_and_rehash_if_needed(
            payload.password, user.hashed_password
        )
        if not is_valid:
            await self._register_failed_attempt(user)
            raise InvalidCredentialsError()

        if new_hash is not None:
            user.hashed_password = new_hash
            await self._users.update(user)

        if not user.is_active:
            raise AccountInactiveError()
        if not user.is_verified:
            raise AccountNotVerifiedError()

        await self._users.reset_failed_attempts(user)

        if user.mfa_enabled:
            challenge = JWTHandler.create_mfa_challenge_token(user.id)
            return MFAChallengeResponse(challenge_token=challenge.token)

        return await self._issue_full_login(user, ip_address=ip_address, device_info=device_info)

    async def verify_mfa(
        self, payload: VerifyMFARequest, *, ip_address: str, device_info: str | None
    ) -> TokenResponse:
        """Conclui o login após validação do código TOTP (`POST /auth/mfa/verify`)."""
        claims = JWTHandler.decode(payload.challenge_token, expected_type=TokenType.MFA_CHALLENGE)
        user = await self._users.get_by_id(claims.sub)

        if user is None or not user.mfa_enabled or not user.mfa_secret:
            raise InvalidTokenError("Desafio de MFA inválido.")

        if not MFAHandler.verify_code(user.mfa_secret, payload.code):
            raise InvalidMFACodeError()

        return await self._issue_full_login(user, ip_address=ip_address, device_info=device_info)

    async def enable_mfa(self, user: User) -> tuple[str, str]:
        """
        Ativa MFA para o usuário autenticado (`POST /auth/mfa/enable`).

        Retorna `(secret, qr_code_uri)` — a camada de API os envolve em
        `EnableMFAResponse`.
        """
        secret = MFAHandler.generate_secret()
        user.mfa_secret = secret
        user.mfa_enabled = True
        await self._users.update(user)
        qr_code_uri = MFAHandler.build_qr_code_uri(secret, account_email=user.email)
        return secret, qr_code_uri

    async def _issue_full_login(
        self, user: User, *, ip_address: str, device_info: str | None
    ) -> TokenResponse:
        """
        Cria um novo registro de `Session` e emite o par access/refresh
        token com a claim `sid` apontando para essa sessão — usado
        apenas no login inicial e na conclusão do desafio de MFA, onde
        um novo "dispositivo logado" de fato nasce.

        A `Session` precisa ser criada *antes* dos tokens porque seu ID
        (gerado no `flush()`) é embutido como claim `sid`, permitindo
        que `POST /auth/logout` saiba qual sessão revogar a partir do
        próprio access token, sem exigir esse dado no corpo da
        requisição.
        """
        session = await self._sessions.create(
            Session(user_id=user.id, device_info=device_info, ip_address=ip_address)
        )
        return await self._issue_token_pair(user, session_id=session.id)

    async def _issue_token_pair(
        self, user: User, *, session_id: uuid.UUID | None = None
    ) -> TokenResponse:
        """
        Emite apenas o par access/refresh token, sem criar uma nova
        `Session`.

        Usado pela rotação de refresh token (`refresh()`): a sessão do
        dispositivo já existe desde o login original — rotacionar
        tokens não deve multiplicar registros de `Session` a cada
        chamada a `/auth/refresh`. Quando `session_id` é informado
        (login inicial), ele é embutido nos tokens via claim `sid`.
        """
        access = JWTHandler.create_access_token(user.id, session_id=session_id)
        refresh = JWTHandler.create_refresh_token(user.id, session_id=session_id)

        await self._refresh_tokens.create(
            RefreshToken(
                user_id=user.id,
                token_hash=JWTHandler.hash_token(refresh.token),
                expires_at=refresh.expires_at,
            )
        )

        expires_in = int((access.expires_at - utcnow()).total_seconds())
        return TokenResponse(
            access_token=access.token,
            refresh_token=refresh.token,
            expires_in=expires_in,
        )

    async def _register_failed_attempt(self, user: User) -> None:
        """Incrementa tentativas falhas e aplica bloqueio se o limite for atingido (Seção 7)."""
        attempts = await self._users.increment_failed_attempts(user)
        if attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
            locked_until = utcnow() + timedelta(minutes=settings.ACCOUNT_LOCKOUT_MINUTES)
            await self._users.set_lock(user, locked_until=locked_until)

    # --- Refresh / Logout ---

    async def refresh(self, payload: RefreshRequest) -> TokenResponse:
        """
        Rotaciona o refresh token (Seção 7): o token antigo é revogado e
        um novo par é emitido. Reuso de um refresh token já revogado
        dispara a revogação de todas as sessões do usuário.
        """
        claims = JWTHandler.decode(payload.refresh_token, expected_type=TokenType.REFRESH)
        token_hash = JWTHandler.hash_token(payload.refresh_token)
        stored = await self._refresh_tokens.get_by_token_hash(token_hash)

        if stored is None:
            raise InvalidTokenError("Refresh token não reconhecido.")

        if stored.revoked:
            # Proteção contra token replay (Seção 7): revoga tudo.
            await self._refresh_tokens.revoke_all_for_user(claims.sub)
            await self._sessions.revoke_all_for_user(claims.sub)
            raise TokenRevokedError()

        await self._refresh_tokens.revoke(stored)

        user = await self._users.get_by_id(claims.sub)
        if user is None or not user.is_active:
            raise AccountInactiveError()

        if claims.sid is not None:
            session = await self._sessions.get_by_id(claims.sid)
            if session is not None and not session.revoked:
                await self._sessions.touch_last_active(session, timestamp=utcnow())

        return await self._issue_token_pair(user, session_id=claims.sid)

    async def logout(self, *, refresh_token: str | None, session_id: uuid.UUID | None) -> None:
        """Revoga o refresh token e/ou sessão do dispositivo atual (`POST /auth/logout`)."""
        if refresh_token:
            token_hash = JWTHandler.hash_token(refresh_token)
            stored = await self._refresh_tokens.get_by_token_hash(token_hash)
            if stored is not None and not stored.revoked:
                await self._refresh_tokens.revoke(stored)

        if session_id is not None:
            session = await self._sessions.get_by_id(session_id)
            if session is not None and not session.revoked:
                await self._sessions.revoke(session)

    async def logout_all(self, user_id: uuid.UUID) -> None:
        """Revoga todas as sessões e refresh tokens do usuário (`POST /auth/logout-all`)."""
        await self._refresh_tokens.revoke_all_for_user(user_id)
        await self._sessions.revoke_all_for_user(user_id)

    # --- Recuperação de senha / confirmação de e-mail ---

    async def forgot_password(self, payload: ForgotPasswordRequest) -> None:
        """
        Inicia a recuperação de senha (`POST /auth/password/forgot`).

        Sempre retorna silenciosamente (mesmo se o e-mail não existir)
        para não vazar quais e-mails estão cadastrados (Seção 8).
        """
        user = await self._users.get_by_email(payload.email)
        if user is None:
            return
        reset_token = JWTHandler.create_password_reset_token(user.id)
        await self._email_client.send_password_reset(to=user.email, token=reset_token.token)

    async def reset_password(self, payload: ResetPasswordRequest) -> None:
        """
        Confirma a redefinição de senha (`POST /auth/password/reset`).

        Revoga todas as sessões/refresh tokens existentes como medida de
        segurança — uma senha pode ter sido redefinida justamente porque
        foi comprometida.
        """
        claims = JWTHandler.decode(payload.token, expected_type=TokenType.PASSWORD_RESET)
        user = await self._users.get_by_id(claims.sub)
        if user is None:
            raise InvalidTokenError("Token de redefinição de senha inválido.")

        user.hashed_password = PasswordHandler.hash(payload.new_password)
        await self._users.update(user)
        await self._refresh_tokens.revoke_all_for_user(user.id)
        await self._sessions.revoke_all_for_user(user.id)

    async def confirm_email(self, payload: ConfirmEmailRequest) -> None:
        """Confirma o e-mail do usuário (`POST /auth/email/confirm`)."""
        claims = JWTHandler.decode(payload.token, expected_type=TokenType.EMAIL_CONFIRMATION)
        user = await self._users.get_by_id(claims.sub)
        if user is None:
            raise InvalidTokenError("Token de confirmação de e-mail inválido.")

        user.is_verified = True
        await self._users.update(user)
