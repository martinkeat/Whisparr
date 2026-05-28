import aiohttp
from .base import ServiceAdapter, HealthStatus
from typing import Dict, List, Optional, Any

class QBittorrentAdapter(ServiceAdapter):
    def __init__(self, internal_url: str = "http://127.0.0.1:8091"):
        super().__init__("qbittorrent", internal_url)

    async def health_check(self) -> HealthStatus:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.internal_url}/api/v2/app/version", timeout=2) as resp:
                    if resp.status == 200:
                        return HealthStatus.HEALTHY
                    return HealthStatus.ERROR
        except Exception:
            # TODO: Check if process is actually running via s6-overlay status
            return HealthStatus.STOPPED

    async def version(self) -> Optional[str]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.internal_url}/api/v2/app/version") as resp:
                    if resp.status == 200:
                        return await resp.text()
        except Exception:
            return None
        return None

    async def get_status(self) -> Dict[str, Any]:
        # Placeholder for unified status model
        return {
            "name": self.name,
            "version": await self.version(),
            "health": await self.health_check()
        }

    async def collect_logs(self, lines: int = 100) -> List[str]:
        return ["qBittorrent logs placeholder"]

    async def get_active_downloads(self) -> int:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.internal_url}/api/v2/torrents/info?filter=downloading", timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return len(data)
        except Exception:
            pass
        return 0

