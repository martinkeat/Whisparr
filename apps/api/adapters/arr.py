import aiohttp
from .base import ServiceAdapter, HealthStatus
from typing import Dict, List, Optional, Any

class ArrAdapter(ServiceAdapter):
    def __init__(self, name: str, internal_url: str):
        super().__init__(name, internal_url)
        self.api_key: Optional[str] = None

    async def health_check(self) -> HealthStatus:
        if not self.api_key:
            return HealthStatus.UNCONFIGURED
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"X-Api-Key": self.api_key}
                async with session.get(f"{self.internal_url}/api/v3/system/status", headers=headers, timeout=2) as resp:
                    if resp.status == 200:
                        return HealthStatus.HEALTHY
                    return HealthStatus.ERROR
        except Exception:
            return HealthStatus.STOPPED

    async def version(self) -> Optional[str]:
        if not self.api_key:
            return None
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"X-Api-Key": self.api_key}
                async with session.get(f"{self.internal_url}/api/v3/system/status", headers=headers, timeout=2) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("version")
        except Exception:
            return None
        return None

    async def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "health": await self.health_check(),
            "api_key_set": self.api_key is not None
        }

    async def collect_logs(self, lines: int = 100) -> List[str]:
        return [f"{self.name} logs placeholder"]

    async def get_movie_count(self) -> int:
        if not self.api_key:
            return 0
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"X-Api-Key": self.api_key}
                async with session.get(f"{self.internal_url}/api/v3/movie", headers=headers, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return len(data)
        except Exception:
            pass
        return 0

    async def get_episode_count(self) -> int:
        if not self.api_key:
            return 0
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"X-Api-Key": self.api_key}
                async with session.get(f"{self.internal_url}/api/v3/series", headers=headers, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Sum up the episodeFileCount or episodeCount
                        return sum(series.get('statistics', {}).get('episodeFileCount', 0) for series in data)
        except Exception:
            pass
        return 0


class SonarrAdapter(ArrAdapter):
    def __init__(self, internal_url: str = "http://127.0.0.1:8989"):
        super().__init__("sonarr", internal_url)

class RadarrAdapter(ArrAdapter):
    def __init__(self, internal_url: str = "http://127.0.0.1:7878"):
        super().__init__("radarr", internal_url)

class LidarrAdapter(ArrAdapter):
    def __init__(self, internal_url: str = "http://127.0.0.1:8686"):
        super().__init__("lidarr", internal_url)

    async def health_check(self) -> HealthStatus:
        if not self.api_key:
            return HealthStatus.UNCONFIGURED
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"X-Api-Key": self.api_key}
                async with session.get(f"{self.internal_url}/api/v1/system/status", headers=headers, timeout=2) as resp:
                    if resp.status == 200:
                        return HealthStatus.HEALTHY
                    return HealthStatus.ERROR
        except Exception:
            return HealthStatus.STOPPED


class WhisparrAdapter(ArrAdapter):
    def __init__(self, internal_url: str = "http://127.0.0.1:6969"):
        super().__init__("whisparr", internal_url)

class ProwlarrAdapter(ArrAdapter):
    def __init__(self, internal_url: str = "http://127.0.0.1:9696"):
        super().__init__("prowlarr", internal_url)

    async def health_check(self) -> HealthStatus:
        if not self.api_key:
            return HealthStatus.UNCONFIGURED
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"X-Api-Key": self.api_key}
                async with session.get(f"{self.internal_url}/api/v1/system/status", headers=headers, timeout=2) as resp:
                    if resp.status == 200:
                        return HealthStatus.HEALTHY
                    return HealthStatus.ERROR
        except Exception:
            return HealthStatus.STOPPED
