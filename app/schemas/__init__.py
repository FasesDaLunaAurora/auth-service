"""
Pacote `app/schemas`.

Re-exporta todos os schemas para facilitar importações nas camadas
superiores (api/routes) sem precisar conhecer o módulo exato:

    from app.schemas import LoginRequest, TokenResponse
"""

from app.schemas.auth_schema import (
    EmailConfirmRequest,
    EmailConfirmResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LogoutRequest,
    LogoutResponse,
    MFAEnableResponse,
    MFAVerifyRequest,
    MFAVerifyResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    TokenResponse,
)
from app.schemas.base_schema import (
    ErrorBody,
    ErrorDetail,
    ErrorResponse,
    OrmBaseModel,
    PaginatedResponse,
    PaginationMeta,
)
from app.schemas.permission_schema import (
    CreatePermissionRequest,
    PermissionListResponse,
    PermissionResponse,
    UpdatePermissionRequest,
)
from app.schemas.role_schema import (
    AssignPermissionToRoleRequest,
    AssignRoleRequest,
    CreateRoleRequest,
    PermissionAssignmentResponse,
    RevokePermissionFromRoleRequest,
    RevokeRoleRequest,
    RoleAssignmentResponse,
    RoleListResponse,
    RoleResponse,
    UpdateRoleRequest,
)
from app.schemas.session_schema import (
    RevokeSessionResponse,
    SessionListResponse,
    SessionResponse,
)
from app.schemas.token_schema import (
    AccessTokenPayload,
    RefreshTokenPayload,
    SpecialTokenPayload,
    TokenPairSchema,
    TokenPayload,
)
from app.schemas.user_schema import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    RoleMinimalResponse,
    UpdateProfileRequest,
    UpdateUserRequest,
    UserAdminResponse,
    UserListResponse,
    UserResponse,
    UserWithRolesResponse,
)

__all__ = [
    # base
    "OrmBaseModel",
    "ErrorBody",
    "ErrorDetail",
    "ErrorResponse",
    "PaginatedResponse",
    "PaginationMeta",
    # auth
    "RegisterRequest",
    "RegisterResponse",
    "LoginRequest",
    "TokenResponse",
    "RefreshRequest",
    "LogoutRequest",
    "LogoutResponse",
    "ForgotPasswordRequest",
    "ForgotPasswordResponse",
    "ResetPasswordRequest",
    "ResetPasswordResponse",
    "EmailConfirmRequest",
    "EmailConfirmResponse",
    "MFAEnableResponse",
    "MFAVerifyRequest",
    "MFAVerifyResponse",
    # token (interno)
    "TokenPayload",
    "AccessTokenPayload",
    "RefreshTokenPayload",
    "SpecialTokenPayload",
    "TokenPairSchema",
    # user
    "UserResponse",
    "UserAdminResponse",
    "UserWithRolesResponse",
    "UserListResponse",
    "RoleMinimalResponse",
    "UpdateProfileRequest",
    "UpdateUserRequest",
    "ChangePasswordRequest",
    "ChangePasswordResponse",
    # role
    "RoleResponse",
    "RoleListResponse",
    "CreateRoleRequest",
    "UpdateRoleRequest",
    "AssignRoleRequest",
    "RevokeRoleRequest",
    "RoleAssignmentResponse",
    "AssignPermissionToRoleRequest",
    "RevokePermissionFromRoleRequest",
    "PermissionAssignmentResponse",
    # permission
    "PermissionResponse",
    "PermissionListResponse",
    "CreatePermissionRequest",
    "UpdatePermissionRequest",
    # session
    "SessionResponse",
    "SessionListResponse",
    "RevokeSessionResponse",
]
