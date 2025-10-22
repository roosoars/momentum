from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from ....application.services.auth_service import AuthService
from ....domain.models import User
from ....core.dependencies import get_auth_service
from ...api.dependencies import require_admin_user
from ...api.schemas.auth import CodePayload, PasswordPayload, PhonePayload

router = APIRouter(prefix="/api/auth", tags=["Telegram Authentication"])


@router.get("/status")
async def auth_status(
    auth_service: AuthService = Depends(get_auth_service),
    _: User = Depends(require_admin_user),
) -> Dict[str, Any]:
    return auth_service.status()


@router.post("/send-code")
async def auth_send_code(
    payload: PhonePayload,
    auth_service: AuthService = Depends(get_auth_service),
    _: User = Depends(require_admin_user),
) -> Dict[str, Any]:
    try:
        return await auth_service.send_login_code(payload.phone)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/verify-code")
async def auth_verify_code(
    payload: CodePayload,
    auth_service: AuthService = Depends(get_auth_service),
    _: User = Depends(require_admin_user),
) -> Dict[str, Any]:
    try:
        return await auth_service.verify_login_code(payload.code)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/password")
async def auth_password(
    payload: PasswordPayload,
    auth_service: AuthService = Depends(get_auth_service),
    _: User = Depends(require_admin_user),
) -> Dict[str, Any]:
    try:
        return await auth_service.provide_password(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def auth_logout(
    auth_service: AuthService = Depends(get_auth_service),
    _: User = Depends(require_admin_user),
) -> None:
    await auth_service.log_out()
