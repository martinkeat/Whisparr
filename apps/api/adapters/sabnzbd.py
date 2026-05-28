import aiohttp
from .base import ServiceAdapter, HealthStatus
from typing import Dict, List, Optional, Any

class SABnzbdAdapter(ServiceAdapter):
    def __init__(self, internal_url: str = "http://127.0.0.1:8085"):
        super().__init__("sabnzbd", internal_url)
        self.api_key: Optional[str] = None


    async def health_check(self) -> HealthStatus:
        try:
            async with aiohttp.ClientSession() as session:
                # SABnzbd needs an API key even for basic version check usually,
                # but we'll try a simple connection test first
                async with session.get(f"{self.internal_url}/api?mode=version", timeout=2) as resp:
                    if resp.status == 200:
                        return HealthStatus.HEALTHY
                    return HealthStatus.ERROR
        except Exception:
            return HealthStatus.STOPPED

    async def version(self) -> Optional[str]:
        return "SABnzbd version placeholder"

    async def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": await self.version(),
            "health": await self.health_check()
        }

    async def collect_logs(self, lines: int = 100) -> List[str]:
        return ["SABnzbd logs placeholder"]

    async def get_active_downloads(self) -> int:
        if not self.api_key:
            return 0
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.internal_url}/api?mode=queue&output=json&apikey={self.api_key}", timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        queue = data.get("queue", {})
                        # Count downloading or queued jobs
                        jobs = queue.get("slots", [])
                        return len([j for j in jobs if j.get("status") in ("Downloading", "Queued")])
        except Exception:
            pass
        return 0

