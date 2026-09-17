import json
import logging
from typing import Any, Callable, Coroutine
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam
from app.config import get_settings

logger = logging.getLogger(__name__)

class LLMClient:
    """Async client for Ollama LLM via OpenAI-compatible API."""
    
    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(
            base_url=f"{settings.ollama_base_url}/v1",
            api_key="ollama",  # Ollama doesn't need a real key
        )
        self.model = settings.ollama_model
        self.temperature = settings.ollama_temperature
        self.num_ctx = settings.ollama_num_ctx
    
    async def chat(
        self,
        messages: list[ChatCompletionMessageParam],
        tools: list[ChatCompletionToolParam] | None = None,
        temperature: float | None = None,
    ) -> Any:
        """Send a chat completion request, optionally with tools."""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "extra_body": {"num_ctx": self.num_ctx}
        }
        
        if tools:
            kwargs["tools"] = tools
            
        try:
            response = await self.client.chat.completions.create(**kwargs)
            return response
        except Exception as e:
            logger.error(f"Error in chat completion: {e}")
            raise
    
    async def chat_with_tools(
        self,
        messages: list[ChatCompletionMessageParam],
        tools: list[ChatCompletionToolParam],
        tool_executor: Callable[[str, dict], Coroutine[Any, Any, Any]],
        max_tool_rounds: int = 5,
    ) -> tuple[str, list[dict]]:
        """Complete a multi-round tool-calling conversation.
        
        This method handles the full tool-calling loop:
        1. Send messages + tools to the model
        2. If model returns tool_calls, execute them via tool_executor
        3. Append tool results to messages
        4. Repeat until model returns a final text response or max rounds reached
        
        Returns:
            tuple of (final_response_text, list_of_tool_calls_made)
        """
        current_messages = list(messages)
        tool_calls_made = []
        
        for round_idx in range(max_tool_rounds):
            logger.debug(f"Starting tool round {round_idx + 1}/{max_tool_rounds}")
            response = await self.chat(
                messages=current_messages,
                tools=tools
            )
            
            message = response.choices[0].message
            current_messages.append(message)
            
            if not message.tool_calls:
                # No tools called, return final text
                return message.content or "", tool_calls_made
                
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                func_args_str = tool_call.function.arguments
                
                try:
                    func_args = json.loads(func_args_str)
                except json.JSONDecodeError:
                    func_args = {}
                    
                logger.info(f"Model called tool: {func_name} with args: {func_args}")
                
                try:
                    # Execute tool
                    result = await tool_executor(func_name, func_args)
                except Exception as e:
                    logger.error(f"Error executing tool {func_name}: {e}")
                    result = {"error": str(e)}
                
                result_str = json.dumps(result)
                    
                tool_calls_made.append({
                    "name": func_name,
                    "arguments": func_args,
                    "result": result,
                })
                
                current_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": func_name,
                    "content": result_str
                })
                
        # If we reached max_tool_rounds without returning, just get a final summary without tools
        logger.warning(f"Reached max tool rounds ({max_tool_rounds})")
        final_response = await self.chat(messages=current_messages)
        return final_response.choices[0].message.content or "", tool_calls_made
    
    async def is_available(self) -> bool:
        """Check if Ollama is reachable."""
        try:
            await self.client.models.list()
            return True
        except Exception as e:
            logger.error(f"Ollama availability check failed: {e}")
            return False
