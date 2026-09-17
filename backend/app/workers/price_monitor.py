import asyncio
import logging
from datetime import datetime, UTC
from uuid import UUID
import httpx
from sqlalchemy import select
from app.workers.celery_app import celery_app
from app.models.alert import Alert
from app.db.session import async_session_factory
from app.config import get_settings

logger = logging.getLogger(__name__)

async def fetch_price(asset_type: str, symbol: str) -> float | None:
    settings = get_settings()
    asset = asset_type.lower()
    sym = symbol.strip().lower()

    if asset in ("crypto", "cryptocurrency"):
        ticker_map = {
            'btc': 'bitcoin',
            'eth': 'ethereum',
            'sol': 'solana',
            'ada': 'cardano',
            'xrp': 'ripple',
            'doge': 'dogecoin',
            'dot': 'polkadot',
            'matic': 'matic-network',
            'bnb': 'binancecoin',
        }
        coin_id = ticker_map.get(sym, sym)
        url = f"{settings.coingecko_api_url}/simple/price"
        params = {"ids": coin_id, "vs_currencies": "usd"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url, params=params)
                if res.status_code == 200:
                    data = res.json()
                    if coin_id in data and "usd" in data[coin_id]:
                        return float(data[coin_id]["usd"])
        except Exception as e:
            logger.error(f"Error fetching crypto price for {symbol}: {e}")
        return None

    elif asset in ("stock", "action", "equity"):
        if not settings.finnhub_api_key:
            logger.warning("Finnhub API key not configured. Cannot monitor stock alerts.")
            return None
        url = "https://finnhub.io/api/v1/quote"
        params = {"symbol": symbol.upper(), "token": settings.finnhub_api_key}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url, params=params)
                if res.status_code == 200:
                    data = res.json()
                    price = data.get("c")
                    if price and price > 0:
                        return float(price)
        except Exception as e:
            logger.error(f"Error fetching stock price for {symbol}: {e}")
        return None

    return None

async def _check_alerts_async():
    async with async_session_factory() as db:
        result = await db.execute(
            select(Alert).where(Alert.is_active == True, Alert.is_triggered == False)
        )
        active_alerts = result.scalars().all()
        if not active_alerts:
            return

        logger.info(f"Checking {len(active_alerts)} active market alerts...")

        price_cache: dict[tuple[str, str], float | None] = {}

        for alert in active_alerts:
            cache_key = (alert.asset_type.lower(), alert.symbol.upper())
            if cache_key not in price_cache:
                price_cache[cache_key] = await fetch_price(alert.asset_type, alert.symbol)

            current_price = price_cache[cache_key]
            if current_price is None:
                continue

            alert.current_price = current_price

            triggered = False
            cond = alert.condition.lower()
            if cond in ("above", "greater_than", ">", ">="):
                triggered = current_price >= alert.threshold
            elif cond in ("below", "less_than", "<", "<="):
                triggered = current_price <= alert.threshold

            if triggered:
                alert.is_triggered = True
                alert.triggered_at = datetime.now(UTC)
                logger.info(
                    f"🚨 ALERT TRIGGERED: User {alert.user_id} - {alert.symbol} ({alert.asset_type}) "
                    f"hit {current_price} (condition: {alert.condition} {alert.threshold})"
                )

        await db.commit()

@celery_app.task(name="check_market_alerts")
def check_market_alerts():
    """Periodic task that checks current prices against user-defined alerts."""
    asyncio.run(_check_alerts_async())
