import logging
from typing import Any
import httpx
from app.core.base_tool import BaseTool, ToolParameter

logger = logging.getLogger(__name__)

class CryptoTool(BaseTool):
    """Herramienta para obtener precios y datos de criptomonedas."""
    
    TICKER_MAP = {
        'btc': 'bitcoin',
        'eth': 'ethereum',
        'sol': 'solana',
        'ada': 'cardano',
        'xrp': 'ripple',
        'doge': 'dogecoin',
        'dot': 'polkadot',
        'matic': 'matic-network',
        'bnb': 'binancecoin',
        'usdt': 'tether',
        'usdc': 'usd-coin'
    }
    
    @property
    def name(self) -> str:
        return "get_crypto_price"
    
    @property
    def description(self) -> str:
        return "Get the current price, market cap, and 24h change for a cryptocurrency. Use when the user asks about crypto prices, Bitcoin, Ethereum, or any cryptocurrency."
    
    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="coin_id",
                type="string",
                description="CoinGecko coin ID (e.g., 'bitcoin', 'ethereum', 'solana', 'cardano') or ticker symbol",
                required=True
            ),
            ToolParameter(
                name="currency",
                type="string",
                description="Currency for the price",
                required=False,
                enum=['eur', 'usd'],
                default='eur'
            )
        ]
    
    async def execute(self, **kwargs) -> dict[str, Any]:
        """Obtiene el precio de una criptomoneda usando CoinGecko."""
        coin_id = kwargs.get("coin_id", "").lower()
        if not coin_id:
            return {"error": "coin_id is required"}
            
        currency = kwargs.get("currency", "eur").lower()
        
        # Map common tickers to CoinGecko IDs
        if coin_id in self.TICKER_MAP:
            coin_id = self.TICKER_MAP[coin_id]
            
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": coin_id,
            "vs_currencies": currency,
            "include_24hr_change": "true",
            "include_market_cap": "true",
            "include_24hr_vol": "true"
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, params=params)
                if response.status_code != 200:
                    return {"error": f"CoinGecko API error: HTTP {response.status_code}"}
                data = response.json()
                
            if coin_id not in data:
                return {"error": f"Coin '{coin_id}' not found"}
                
            coin_data = data[coin_id]
            return {
                "coin": coin_id.capitalize(),
                "price": coin_data.get(currency),
                "change_24h_percent": coin_data.get(f"{currency}_24h_change"),
                "market_cap": coin_data.get(f"{currency}_market_cap"),
                "volume_24h": coin_data.get(f"{currency}_24h_vol"),
                "currency": currency.upper()
            }
        except Exception as e:
            logger.error(f"Error fetching crypto price: {e}")
            return {"error": "Failed to fetch crypto price"}
