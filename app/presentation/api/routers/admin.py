from fastapi import APIRouter, Depends, Response, status

from ....application.services.admin_auth_service import AdminAuthService
from ....application.services.strategy_service import StrategyService
from ....application.services.channel_service import ChannelService
from ....domain.models import User
from ....core.dependencies import get_admin_auth_service, get_strategy_service, get_channel_service
from ...api.dependencies import require_admin_user
from ...api.schemas.admin import AdminLoginRequest

router = APIRouter(prefix="/api/admin", tags=["Admin Authentication"])


@router.post("/login")
def admin_login(
    payload: AdminLoginRequest,
    admin_auth: AdminAuthService = Depends(get_admin_auth_service),
) -> dict:
    token = admin_auth.authenticate(payload.email, payload.password)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
def admin_me(current_user: User = Depends(require_admin_user)) -> dict:
    return _serialize_user(current_user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def admin_logout(
    _: User = Depends(require_admin_user),
    strategy_service: StrategyService = Depends(get_strategy_service),
    channel_service: ChannelService = Depends(get_channel_service),
) -> Response:
    """Complete cleanup on admin logout: delete all strategies and clear signal history."""
    # Delete all strategies
    strategies = await strategy_service.list_strategies()
    for strategy in strategies:
        await strategy_service.delete_strategy(strategy.id)

    # Clear signal history
    await channel_service.clear_history()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "is_active": user.is_active,
        "created_at": user.created_at.replace(microsecond=0).isoformat(),
        "updated_at": user.updated_at.replace(microsecond=0).isoformat(),
    }
