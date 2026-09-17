import logging
from typing import Any
import httpx
from app.core.base_tool import BaseTool, ToolParameter
from app.config import get_settings

logger = logging.getLogger(__name__)

class MarketsTool(BaseTool):
    """Herramienta para obtener precios de acciones del mercado."""
    
    @property
    def name(self) -> str:
        return "get_stock_price"
    
    @property
    def description(self) -> str:
        return "Get the current price, change, and key data for a stock. Use when the user asks about stock prices, market data, or how a company is doing in the stock market."
    
    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="symbol",
                type="string",
                description="Stock ticker symbol (e.g., 'AAPL', 'GOOGL', 'TSLA')",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> dict[str, Any]:
        """Obtiene el precio de una acción usando la API de Finnhub."""
        settings = get_settings()
        if not getattr(settings, 'finnhub_api_key', None):
            return {"error": "Finnhub API key not configured"}
            
        symbol = kwargs.get("symbol")
        if not symbol:
            return {"error": "Symbol is required"}
            
        url = "https://finnhub.io/api/v1/quote"
        params = {"symbol": symbol.upper(), "token": settings.finnhub_api_key}
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, params=params)
                data = response.json()
                
            if "error" in data:
                return {"error": data["error"]}
                
            # If all returned fields are 0, the symbol is likely invalid or has no data
            if all(v == 0 for k, v in data.items() if k in ['c', 'd', 'dp', 'h', 'l', 'o', 'pc']):
                return {"error": f"Invalid symbol or no data found for {symbol}"}
                
            return {
                "symbol": symbol.upper(),
                "price": data.get("c"),
                "change": data.get("d"),
                "change_percent": data.get("dp"),
                "day_high": data.get("h"),
                "day_low": data.get("l"),
                "open": data.get("o"),
                "previous_close": data.get("pc")
            }
        except Exception as e:
            logger.error(f"Error fetching stock price: {e}")
            return {"error": "Failed to fetch stock price"}
