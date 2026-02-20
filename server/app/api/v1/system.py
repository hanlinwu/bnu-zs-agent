"""Public system settings APIs."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.system_config_service import get_system_basic_config

router = APIRouter()


@router.get("/basic")
async def get_system_basic(
    db: AsyncSession = Depends(get_db),
):
    """Get public system name and logo."""
    config = await get_system_basic_config(db)
    return {"key": "system_basic", "value": config}
