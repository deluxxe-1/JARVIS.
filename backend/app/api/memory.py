import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.core.memory_manager import MemoryManager
from app.schemas.memory import MemoryCreate, MemoryUpdate, MemoryResponse, MemoryListResponse

router = APIRouter(tags=["memory"])


@router.get("", response_model=MemoryListResponse)
async def list_memories(
    category: str | None = Query(None),
    source: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the user's memories with optional filtering."""
    manager = MemoryManager(db)
    memories, total = await manager.list_memories(
        user_id=current_user.id,
        category=category,
        source=source,
        limit=limit,
        offset=offset,
    )
    return MemoryListResponse(
        memories=[MemoryResponse.model_validate(m) for m in memories],
        total=total,
    )


@router.post("", response_model=MemoryResponse, status_code=201)
async def create_memory(
    data: MemoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually add a memory."""
    manager = MemoryManager(db)
    memory = await manager.add_explicit_memory(
        user_id=current_user.id,
        content=data.content,
        category=data.category,
    )
    return MemoryResponse.model_validate(memory)


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a memory."""
    manager = MemoryManager(db)
    success = await manager.forget_memory(
        user_id=current_user.id,
        memory_id=memory_id,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"status": "deleted", "id": str(memory_id)}
