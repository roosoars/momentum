from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from ....application.services.message_service import MessageQueryService
from ....domain.models import User
from ....core.dependencies import get_message_service
from ...api.dependencies import require_admin_user

router = APIRouter(prefix="/api/messages", tags=["Messages"])


@router.get("")
async def list_messages(
    limit: int = Query(default=200, ge=1, le=1000),
    channel_id: Optional[str] = None,
    message_service: MessageQueryService = Depends(get_message_service),
    _: User = Depends(require_admin_user),
) -> Dict[str, Any]:
    return message_service.get_recent_messages(limit=limit, channel_id=channel_id)
