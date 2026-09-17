import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.llm_client import LLMClient
from app.core.memory_manager import MemoryManager
from app.core.tool_registry import tool_registry
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.chat import ChatRequest, ChatResponse, ToolCallInfo

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are ARIA, a highly capable multilingual personal AI assistant. You help the user with navigation, news, financial markets, and general knowledge.

Key behaviors:
- Respond in the same language the user uses (Spanish, English, or any other language)
- Be concise but helpful — don't over-explain unless asked
- When you have tools available that can answer the user's question, USE THEM. Don't guess or make up data.
- For prices, routes, or news — always use the appropriate tool to get real-time data
- When the user says "remember that..." or "recuerda que...", acknowledge and confirm you'll remember it
- When the user says "forget that..." or "olvida que...", acknowledge and confirm
- You have memory of past conversations — use the provided context to personalize responses
- Be natural and conversational, like a smart friend, not a formal assistant
"""

class Orchestrator:
    """Central orchestrator that processes user messages through the full pipeline.
    
    Flow:
    1. Retrieve relevant memories (RAG)
    2. Build prompt with system message + memories + conversation history + user message
    3. Send to LLM with available tools
    4. Handle tool calls (may be multi-round)
    5. Get final response
    6. Save conversation to database
    7. Trigger memory extraction in background
    8. Return response
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = LLMClient()
        self.memory_manager = MemoryManager(db)
        self.settings = get_settings()
    
    async def process_message(
        self,
        user_id: uuid.UUID,
        request: ChatRequest,
    ) -> ChatResponse:
        """Process a user message and return ARIA's response."""
        
        # 1. Get or create conversation
        conversation = await self._get_or_create_conversation(
            user_id=user_id,
            conversation_id=request.conversation_id,
            device=request.device,
        )
        
        # 2. Check for explicit memory commands
        memory_command = self._detect_memory_command(request.message)
        if memory_command:
            return await self._handle_memory_command(
                user_id=user_id,
                conversation=conversation,
                command=memory_command,
                original_message=request.message,
            )
        
        # 3. Retrieve relevant memories (RAG)
        memories = await self.memory_manager.retrieve_relevant(
            user_id=user_id,
            query=request.message,
        )
        memory_context = await self.memory_manager.format_memories_as_context(memories)
        
        # 4. Load recent conversation history (last N messages from this conversation)
        history = await self._get_conversation_history(conversation.id, limit=20)
        
        # 5. Build messages for the LLM
        messages = self._build_messages(
            memory_context=memory_context,
            history=history,
            user_message=request.message,
        )
        
        # 6. Get available tools
        tools = tool_registry.get_openai_tools()
        
        # 7. Call LLM with tool-calling loop
        async def tool_executor(name: str, args: dict) -> dict:
            return await tool_registry.execute(name, **args)
        
        if tools:
            final_response, tool_calls_made = await self.llm.chat_with_tools(
                messages=messages,
                tools=tools,
                tool_executor=tool_executor,
            )
        else:
            completion = await self.llm.chat(messages)
            final_response = completion.choices[0].message.content or ""
            tool_calls_made = []
        
        # 8. Save messages to database
        await self._save_user_message(conversation.id, request.message)
        
        for tc in tool_calls_made:
            await self._save_tool_message(
                conversation_id=conversation.id,
                tool_name=tc["name"],
                tool_args=tc["arguments"],
                tool_result=tc["result"],
            )
        
        await self._save_assistant_message(conversation.id, final_response)
        
        # 9. Trigger async memory extraction (non-blocking)
        try:
            from app.workers.memory_extractor import extract_memories
            all_msgs = [
                {"role": "user", "content": request.message},
                {"role": "assistant", "content": final_response},
            ]
            extract_memories.delay(str(user_id), all_msgs)
        except Exception as e:
            logger.warning(f"Could not queue memory extraction: {e}")
        
        # 10. Build and return response
        tool_call_infos = [
            ToolCallInfo(
                name=tc["name"],
                arguments=tc["arguments"],
                result=tc["result"],
            )
            for tc in tool_calls_made
        ]
        
        return ChatResponse(
            response=final_response,
            conversation_id=conversation.id,
            tool_calls=tool_call_infos,
            memories_used=len(memories),
        )
    
    def _detect_memory_command(self, message: str) -> Optional[dict]:
        """Detect explicit memory commands in the user's message."""
        msg_lower = message.lower().strip()
        
        # Remember commands
        remember_prefixes = [
            "recuerda que ", "remember that ", "recuerda: ", "remember: ",
            "acuérdate de que ", "acuérdate que ", "no olvides que ",
        ]
        for prefix in remember_prefixes:
            if msg_lower.startswith(prefix):
                content = message[len(prefix):].strip()
                return {"action": "remember", "content": content}
        
        # Forget commands
        forget_prefixes = [
            "olvida que ", "forget that ", "olvida: ", "forget: ",
            "olvídate de que ", "olvídate que ",
        ]
        for prefix in forget_prefixes:
            if msg_lower.startswith(prefix):
                content = message[len(prefix):].strip()
                return {"action": "forget", "content": content}
        
        return None
    
    async def _handle_memory_command(
        self,
        user_id: uuid.UUID,
        conversation: Conversation,
        command: dict,
        original_message: str,
    ) -> ChatResponse:
        """Handle explicit remember/forget commands."""
        if command["action"] == "remember":
            memory = await self.memory_manager.add_explicit_memory(
                user_id=user_id,
                content=command["content"],
            )
            response = f"Entendido, lo recordaré: \"{command['content']}\""
        elif command["action"] == "forget":
            count = await self.memory_manager.forget_by_content(
                user_id=user_id,
                content_query=command["content"],
            )
            if count > 0:
                response = f"Hecho, he olvidado {count} recuerdo(s) relacionados con \"{command['content']}\""
            else:
                response = f"No tengo recuerdos que coincidan con \"{command['content']}\""
        else:
            response = "No entendí el comando de memoria."
        
        # Save the exchange
        await self._save_user_message(conversation.id, original_message)
        await self._save_assistant_message(conversation.id, response)
        
        return ChatResponse(
            response=response,
            conversation_id=conversation.id,
        )
    
    async def _get_or_create_conversation(
        self,
        user_id: uuid.UUID,
        conversation_id: Optional[uuid.UUID],
        device: str,
    ) -> Conversation:
        """Get existing conversation or create a new one."""
        if conversation_id:
            conv = await self.db.get(Conversation, conversation_id)
            if conv and conv.user_id == user_id:
                return conv
        
        # Create new conversation
        conv = Conversation(
            user_id=user_id,
            device=device,
        )
        self.db.add(conv)
        await self.db.commit()
        await self.db.refresh(conv)
        return conv
    
    async def _get_conversation_history(
        self,
        conversation_id: uuid.UUID,
        limit: int = 20,
    ) -> list[dict]:
        """Get recent messages from a conversation."""
        from sqlalchemy import select
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = list(reversed(result.scalars().all()))
        
        history = []
        for msg in messages:
            if msg.role in ("user", "assistant"):
                history.append({"role": msg.role, "content": msg.content})
        return history
    
    def _build_messages(
        self,
        memory_context: str,
        history: list[dict],
        user_message: str,
    ) -> list[dict]:
        """Build the full message list for the LLM."""
        messages = []
        
        # System prompt with memory context
        system_content = SYSTEM_PROMPT
        if memory_context:
            system_content += f"\n\n{memory_context}"
        messages.append({"role": "system", "content": system_content})
        
        # Conversation history
        messages.extend(history)
        
        # Current user message
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    async def _save_user_message(self, conversation_id: uuid.UUID, content: str) -> Message:
        msg = Message(conversation_id=conversation_id, role="user", content=content)
        self.db.add(msg)
        await self.db.commit()
        return msg
    
    async def _save_assistant_message(self, conversation_id: uuid.UUID, content: str) -> Message:
        msg = Message(conversation_id=conversation_id, role="assistant", content=content)
        self.db.add(msg)
        await self.db.commit()
        return msg
    
    async def _save_tool_message(
        self,
        conversation_id: uuid.UUID,
        tool_name: str,
        tool_args: dict,
        tool_result: dict,
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            role="tool",
            content=f"Tool: {tool_name}",
            tool_name=tool_name,
            tool_args=tool_args,
            tool_result=tool_result,
        )
        self.db.add(msg)
        await self.db.commit()
        return msg
