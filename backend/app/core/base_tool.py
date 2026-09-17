from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel

class ToolParameter(BaseModel):
    """Schema for a tool parameter."""
    name: str
    type: str  # 'string', 'number', 'integer', 'boolean', 'array', 'object'
    description: str
    required: bool = True
    enum: list[str] | None = None
    default: Any = None

class BaseTool(ABC):
    """Abstract base class for all ARIA tools.
    
    To create a new tool, subclass this and implement:
    - name: unique identifier
    - description: what the tool does (the LLM reads this to decide when to use it)
    - parameters: list of ToolParameter
    - execute(): the actual logic
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this tool."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what this tool does. The LLM uses this to decide when to invoke it."""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> list[ToolParameter]:
        """List of parameters this tool accepts."""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> dict[str, Any]:
        """Execute the tool with the given parameters. Returns a dict with the result."""
        pass
    
    def to_openai_tool(self) -> dict:
        """Convert this tool to OpenAI function calling format.
        
        Returns a dict compatible with the OpenAI tools API:
        {
            "type": "function",
            "function": {
                "name": "...",
                "description": "...",
                "parameters": {
                    "type": "object",
                    "properties": {...},
                    "required": [...]
                }
            }
        }
        """
        properties = {}
        required = []
        for param in self.parameters:
            prop: dict = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default
            properties[param.name] = prop
            if param.required:
                required.append(param.name)
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                }
            }
        }
