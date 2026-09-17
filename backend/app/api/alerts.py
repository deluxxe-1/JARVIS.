import uuid
from datetime import datetime, UTC
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.alert import Alert
from app.schemas.alert import AlertCreate, AlertResponse

router = APIRouter(tags=["alerts"])

@router.get("", response_model=list[AlertResponse])
async def list_alerts(
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List market alerts configured for the current user."""
    query = select(Alert).where(Alert.user_id == current_user.id)
    if active_only:
        query = query.where(Alert.is_active == True)
    query = query.order_by(Alert.created_at.desc())
    
    result = await db.execute(query)
    alerts = result.scalars().all()
    return alerts

@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_in: AlertCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new stock or crypto price alert."""
    cond = alert_in.condition.lower()
    valid_conditions = ["above", "below", "greater_than", "less_than", ">", "<", ">=", "<="]
    if cond not in valid_conditions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid condition. Supported: {valid_conditions}"
        )

    asset = alert_in.asset_type.lower()
    if asset not in ("stock", "crypto"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="asset_type must be either 'stock' or 'crypto'"
        )

    alert = Alert(
        user_id=current_user.id,
        asset_type=asset,
        symbol=alert_in.symbol.upper(),
        condition=cond,
        threshold=alert_in.threshold,
        is_active=True,
        is_triggered=False,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert

@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel / deactivate an alert."""
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.user_id == current_user.id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    alert.is_active = False
    await db.commit()
    return {"status": "deactivated", "id": str(alert_id)}
