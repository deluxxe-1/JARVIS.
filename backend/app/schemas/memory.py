from pydantic import BaseModel, ConfigDict
from typing import Optional
import uuid
from datetime import datetime

class MemoryCreate(BaseModel):
    content: str
    category: str = "other"

class MemoryUpdate(BaseModel):
    content: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None

class MemoryResponse(BaseModel):
    id: uuid.UUID
    content: str
    category: str
    source: str
    importance: float
    access_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class MemoryListResponse(BaseModel):
    memories: list[MemoryResponse]
    total: int
