from pydantic import BaseModel
from typing import Optional, Any, List
import uuid

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[uuid.UUID] = None
    device: str = "unknown"

class ToolCallInfo(BaseModel):
    name: str
    arguments: dict[str, Any]
    result: Any

class ChatResponse(BaseModel):
    response: str
    conversation_id: uuid.UUID
    tool_calls: List[ToolCallInfo] = []
    memories_used: int = 0
