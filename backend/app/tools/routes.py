import logging
from typing import Any
import httpx
from app.core.base_tool import BaseTool, ToolParameter
from app.config import get_settings

logger = logging.getLogger(__name__)

class RoutesTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_route"
    
    @property
    def description(self) -> str:
        return (
            "Calculate the fastest driving route between two locations. "
            "Returns estimated travel time, distance, and step-by-step directions. "
            "Use when the user asks about directions, routes, how to get somewhere, "
            "or travel time between places."
        )
    
    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="origin",
                type="string",
                description="Starting location (address, city name, or place name)",
                required=True,
            ),
            ToolParameter(
                name="destination", 
                type="string",
                description="Destination location (address, city name, or place name)",
                required=True,
            ),
            ToolParameter(
                name="mode",
                type="string",
                description="Travel mode",
                required=False,
                enum=["driving", "walking", "bicycling", "transit"],
                default="driving",
            ),
        ]
    
    async def execute(self, **kwargs) -> dict[str, Any]:
        settings = get_settings()
        origin = kwargs.get("origin", "")
        destination = kwargs.get("destination", "")
        mode = kwargs.get("mode", "driving")
        
        if not getattr(settings, 'google_maps_api_key', None):
            return {"error": "Google Maps API key not configured"}
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                "https://maps.googleapis.com/maps/api/directions/json",
                params={
                    "origin": origin,
                    "destination": destination,
                    "mode": mode,
                    "departure_time": "now",
                    "language": "es",  # Spanish results
                    "key": settings.google_maps_api_key,
                },
            )
            data = response.json()
        
        if data.get("status") != "OK" or not data.get("routes"):
            return {"error": f"Could not find route: {data.get('status', 'Unknown error')}"}
        
        route = data["routes"][0]
        leg = route["legs"][0]
        
        # Extract key steps for the summary
        steps = []
        for step in leg["steps"][:8]:  # Limit to 8 main steps
            # Strip HTML tags from instructions
            import re
            instruction = re.sub(r'<[^>]+>', '', step["html_instructions"])
            steps.append({
                "instruction": instruction,
                "distance": step["distance"]["text"],
                "duration": step["duration"]["text"],
            })
        
        return {
            "origin": leg["start_address"],
            "destination": leg["end_address"],
            "distance": leg["distance"]["text"],
            "duration": leg["duration"]["text"],
            "duration_in_traffic": leg.get("duration_in_traffic", {}).get("text", leg["duration"]["text"]),
            "mode": mode,
            "steps": steps,
            "summary": route.get("summary", ""),
        }
