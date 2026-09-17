from pydantic import BaseModel, ConfigDict
from typing import Optional
import uuid
from datetime import datetime

class AlertCreate(BaseModel):
    asset_type: str
    symbol: str
    condition: str
    threshold: float

class AlertResponse(BaseModel):
    id: uuid.UUID
    asset_type: str
    symbol: str
    condition: str
    threshold: float
    current_price: Optional[float] = None
    is_triggered: bool
    is_active: bool
    created_at: datetime
    triggered_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
