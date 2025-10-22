from fastapi import APIRouter, Depends, HTTPException, status

from ....application.services.admin_auth_service import AdminAuthService
from ....domain.models import User
from ....core.dependencies import get_admin_auth_service
from ...api.dependencies import require_admin_user
from ...api.schemas.admin import AdminLoginRequest, AdminRegisterRequest

router = APIRouter(prefix="/api/admin", tags=["Admin Authentication"])


@router.post("/login")
def admin_login(
    payload: AdminLoginRequest,
    admin_auth: AdminAuthService = Depends(get_admin_auth_service),
) -> dict:
    token = admin_auth.authenticate(payload.email, payload.password)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/register")
def admin_register(
    payload: AdminRegisterRequest,
    admin_auth: AdminAuthService = Depends(get_admin_auth_service),
    _: User = Depends(require_admin_user),
) -> dict:
    try:
        user = admin_auth.register(payload.email, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_user(user)


@router.get("/me")
def admin_me(current_user: User = Depends(require_admin_user)) -> dict:
    return _serialize_user(current_user)


def _serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "is_active": user.is_active,
        "created_at": user.created_at.replace(microsecond=0).isoformat(),
        "updated_at": user.updated_at.replace(microsecond=0).isoformat(),
    }
