import logging
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.core.orchestrator import Orchestrator
from app.services.auth import AuthService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message to ARIA and get a response."""
    orchestrator = Orchestrator(db)
    response = await orchestrator.process_message(
        user_id=current_user.id,
        request=request,
    )
    return response


@router.websocket("/ws")
async def chat_websocket(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db),
):
    """WebSocket endpoint for real-time chat.
    
    Protocol:
    1. Client connects and sends first message: {"token": "jwt_token_here"}
    2. Server authenticates and sends: {"type": "auth", "status": "ok"}
    3. Client sends messages: {"message": "...", "conversation_id": "..." (optional), "device": "..."}
    4. Server responds with ChatResponse JSON
    5. On error: {"type": "error", "detail": "..."}
    """
    await websocket.accept()
    
    try:
        # Step 1: Authenticate
        auth_data = await websocket.receive_json()
        token = auth_data.get("token")
        if not token:
            await websocket.send_json({"type": "error", "detail": "Token required"})
            await websocket.close()
            return
        
        auth_service = AuthService(db)
        user_id = auth_service.decode_token(token)
        if not user_id:
            await websocket.send_json({"type": "error", "detail": "Invalid token"})
            await websocket.close()
            return
        
        user = await auth_service.get_user_by_id(user_id)
        if not user or not user.is_active:
            await websocket.send_json({"type": "error", "detail": "User not found"})
            await websocket.close()
            return
        
        await websocket.send_json({"type": "auth", "status": "ok", "username": user.username})
        logger.info(f"WebSocket authenticated: {user.username}")
        
        # Step 2: Message loop
        orchestrator = Orchestrator(db)
        
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "").strip()
            if not message:
                await websocket.send_json({"type": "error", "detail": "Empty message"})
                continue
            
            request = ChatRequest(
                message=message,
                conversation_id=data.get("conversation_id"),
                device=data.get("device", "websocket"),
            )
            
            try:
                response = await orchestrator.process_message(
                    user_id=user.id,
                    request=request,
                )
                await websocket.send_json({
                    "type": "response",
                    "data": response.model_dump(mode="json"),
                })
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await websocket.send_json({"type": "error", "detail": str(e)})
    
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except Exception:
            pass
