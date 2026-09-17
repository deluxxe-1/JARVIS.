import logging
from typing import Any
import httpx
from app.core.base_tool import BaseTool, ToolParameter
from app.config import get_settings

logger = logging.getLogger(__name__)

class NewsTool(BaseTool):
    """Herramienta para buscar y obtener noticias recientes."""
    
    @property
    def name(self) -> str:
        return "get_news"
    
    @property
    def description(self) -> str:
        return "Search for and retrieve recent news articles on a specific topic or general headlines. Use when the user asks about news, current events, or what's happening in the world."
    
    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="Search query / topic. If not provided, returns top headlines",
                required=False
            ),
            ToolParameter(
                name="category",
                type="string",
                description="Category filter",
                required=False,
                enum=['business', 'technology', 'science', 'health', 'sports', 'entertainment', 'general']
            ),
            ToolParameter(
                name="language",
                type="string",
                description="Language code",
                required=False,
                default="es"
            )
        ]
    
    async def execute(self, **kwargs) -> dict[str, Any]:
        """Ejecuta la búsqueda de noticias en NewsAPI."""
        settings = get_settings()
        if not getattr(settings, 'news_api_key', None):
            return {"error": "News API key not configured"}
            
        query = kwargs.get("query")
        category = kwargs.get("category")
        language = kwargs.get("language", "es")
        
        url = "https://newsapi.org/v2/top-headlines"
        params = {"apiKey": settings.news_api_key, "language": language}
        
        if query:
            url = "https://newsapi.org/v2/everything"
            params["q"] = query
        elif category:
            params["category"] = category
            
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, params=params)
                data = response.json()
                
            if data.get("status") != "ok":
                return {"error": f"Error from NewsAPI: {data.get('message', 'Unknown error')}"}
                
            articles = data.get("articles", [])[:5]
            result = []
            for art in articles:
                result.append({
                    "title": art.get("title"),
                    "source": art.get("source", {}).get("name"),
                    "description": art.get("description"),
                    "url": art.get("url"),
                    "publishedAt": art.get("publishedAt")
                })
            return {"articles": result}
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return {"error": "Failed to fetch news"}
