import logging
from typing import Any
from app.core.base_tool import BaseTool

logger = logging.getLogger(__name__)

class ToolRegistry:
    """Dynamic registry for ARIA tools.
    
    Tools register themselves at startup. The orchestrator uses this to:
    1. Get the list of available tools in OpenAI format (for the LLM)
    2. Execute a tool by name when the LLM requests it
    """
    
    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool) -> None:
        """Register a tool. Raises ValueError if name already taken."""
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self._tools.get(name)
    
    async def execute(self, name: str, **kwargs) -> dict[str, Any]:
        """Execute a tool by name with given kwargs."""
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Unknown tool: {name}")
        logger.info(f"Executing tool: {name} with args: {kwargs}")
        try:
            result = await tool.execute(**kwargs)
            logger.info(f"Tool {name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}")
            return {"error": str(e)}
    
    def get_openai_tools(self) -> list[dict]:
        """Get all registered tools in OpenAI function calling format."""
        return [tool.to_openai_tool() for tool in self._tools.values()]
    
    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())
    
    @property
    def count(self) -> int:
        return len(self._tools)


# Global singleton instance
tool_registry = ToolRegistry()
