from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ...application.services.admin_auth_service import AdminAuthService
from ...core.dependencies import get_admin_auth_service

_bearer_scheme = HTTPBearer(auto_error=False)


def require_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    admin_service: AdminAuthService = Depends(get_admin_auth_service),
):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token ausente.")
    return admin_service.get_current_admin(credentials.credentials)
