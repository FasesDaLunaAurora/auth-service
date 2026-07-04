"""
Rotas de autenticação (`/api/v1/auth`, Seção 6).

Regra de camada (Seção 3): rotas recebem a requisição HTTP, validam via
Schema (feito automaticamente pelo FastAPI a partir da assinatura),
chamam o `Service` correspondente e traduzem o retorno em uma
`Response` — nenhuma regra de negócio vive aqui.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, status

from app.api.dependencies.auth_dependency import CurrentTokenPayload, CurrentUser
from app.api.dependencies.db_dependency import AuthServiceDep
from app.schemas.auth_schema import (
    ConfirmEmailRequest,
    EnableMFAResponse,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    VerifyMFARequest,
)
from app.schemas.token_schema import MFAChallengeResponse, TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _client_ip(request: Request) -> str:
    """Extrai o IP do cliente, priorizando `X-Forwarded-For` (mesma lógica do middleware)."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastro de usuário",
)
async def register(payload: RegisterRequest, auth_service: AuthServiceDep) -> RegisterResponse:
    user = await auth_service.register(payload)
    return RegisterResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse | MFAChallengeResponse,
    status_code=status.HTTP_200_OK,
    summary="Login (retorna tokens, ou um desafio de MFA se ativo)",
)
async def login(
    payload: LoginRequest, request: Request, auth_service: AuthServiceDep
) -> TokenResponse | MFAChallengeResponse:
    return await auth_service.login(
        payload,
        ip_address=_client_ip(request),
        device_info=request.headers.get("User-Agent"),
    )


@router.post(
    "/mfa/verify",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Verifica o código MFA e conclui o login",
)
async def verify_mfa(
    payload: VerifyMFARequest, request: Request, auth_service: AuthServiceDep
) -> TokenResponse:
    return await auth_service.verify_mfa(
        payload,
        ip_address=_client_ip(request),
        device_info=request.headers.get("User-Agent"),
    )


@router.post(
    "/mfa/enable",
    response_model=EnableMFAResponse,
    status_code=status.HTTP_200_OK,
    summary="Ativa MFA para o usuário autenticado",
)
async def enable_mfa(current_user: CurrentUser, auth_service: AuthServiceDep) -> EnableMFAResponse:
    secret, qr_code_uri = await auth_service.enable_mfa(current_user)
    return EnableMFAResponse(secret=secret, qr_code_uri=qr_code_uri)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotaciona o refresh token e emite um novo par de tokens",
)
async def refresh_token(payload: RefreshRequest, auth_service: AuthServiceDep) -> TokenResponse:
    return await auth_service.refresh(payload)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoga a sessão/refresh token do dispositivo atual",
)
async def logout(
    payload: LogoutRequest,
    current_user: CurrentUser,
    token_payload: CurrentTokenPayload,
    auth_service: AuthServiceDep,
) -> None:
    await auth_service.logout(refresh_token=payload.refresh_token, session_id=token_payload.sid)


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoga todas as sessões/refresh tokens do usuário",
)
async def logout_all(current_user: CurrentUser, auth_service: AuthServiceDep) -> None:
    await auth_service.logout_all(current_user.id)


@router.post(
    "/password/forgot",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Solicita recuperação de senha",
)
async def forgot_password(payload: ForgotPasswordRequest, auth_service: AuthServiceDep) -> None:
    await auth_service.forgot_password(payload)


@router.post(
    "/password/reset",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Confirma a redefinição de senha",
)
async def reset_password(payload: ResetPasswordRequest, auth_service: AuthServiceDep) -> None:
    await auth_service.reset_password(payload)


@router.post(
    "/email/confirm",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Confirma o e-mail via token",
)
async def confirm_email(payload: ConfirmEmailRequest, auth_service: AuthServiceDep) -> None:
    await auth_service.confirm_email(payload)
