import aiohttp
import asyncio
from core.settings import settings
from typing import Dict, Any

class Provisioner:
    def __init__(self, adapters: Dict[str, Any]):
        self.adapters = adapters

    async def provision_service(self, name: str):
        """Automatically configures a service once it is healthy."""
        if name not in self.adapters:
            return

        adapter = self.adapters[name]
        # Wait for service to be healthy (up to 30s)
        for _ in range(30):
            status = await adapter.get_status()
            if status['health'] == 'healthy':
                break
            await asyncio.sleep(1)
        else:
            print(f"Provisioning timed out for {name}")
            return

        print(f"Provisioning {name}...")
        
        if name in ["sonarr", "radarr", "lidarr", "whisparr"]:
            await self._provision_arr(name)
        elif name == "prowlarr":
            await self._provision_prowlarr()
        elif name == "sabnzbd":
            await self._provision_sabnzbd()

    async def _provision_arr(self, name: str):
        adapter = self.adapters[name]
        api_key = settings.config.services[name].api_key
        url = settings.config.services[name].url
        
        async with aiohttp.ClientSession() as session:
            headers = {"X-Api-Key": api_key}
            
            # 1. Set up Root Folders
            root_folders = {
                "sonarr": "/tv",
                "radarr": "/movies",
                "lidarr": "/music",
                "whisparr": "/adult"
            }
            await session.post(f"{url}/api/v3/rootfolder", headers=headers, json={"path": root_folders[name]})

            # 2. Set up Download Clients (SABnzbd)
            if "sabnzbd" in settings.config.services:
                sab_cfg = settings.config.services["sabnzbd"]
                await session.post(f"{url}/api/v3/downloadclient", headers=headers, json={
                    "enable": True,
                    "name": "SABnzbd (Nexus)",
                    "implementation": "Sabnzbd",
                    "configContract": "SabnzbdSettings",
                    "fields": [
                        {"name": "host", "value": "127.0.0.1"},
                        {"name": "port", "value": 8081},
                        {"name": "apiKey", "value": sab_cfg.api_key}
                    ]
                })

            # 3. Set up Download Clients (qBittorrent)
            if "qbittorrent" in settings.config.services:
                await session.post(f"{url}/api/v3/downloadclient", headers=headers, json={
                    "enable": True,
                    "name": "qBittorrent (Nexus)",
                    "implementation": "QBittorrent",
                    "configContract": "QBittorrentSettings",
                    "fields": [
                        {"name": "host", "value": "127.0.0.1"},
                        {"name": "port", "value": 8091},
                        {"name": "username", "value": "admin"},
                        {"name": "password", "value": "adminadmin"}
                    ]
                })

    async def _provision_prowlarr(self):
        adapter = self.adapters["prowlarr"]
        api_key = settings.config.services["prowlarr"].api_key
        url = settings.config.services["prowlarr"].url
        
        async with aiohttp.ClientSession() as session:
            headers = {"X-Api-Key": api_key}
            
            # Link Prowlarr to Sonarr, Radarr, etc.
            apps = ["sonarr", "radarr", "lidarr", "whisparr"]
            ports = {"sonarr": 8989, "radarr": 7878, "lidarr": 8686, "whisparr": 6969}
            
            for app in apps:
                if app in settings.config.services and settings.config.services[app].enabled:
                    app_cfg = settings.config.services[app]
                    await session.post(f"{url}/api/v1/applications", headers=headers, json={
                        "name": app.capitalize(),
                        "implementation": app.capitalize(),
                        "configContract": f"{app.capitalize()}Settings",
                        "fields": [
                            {"name": "prowlarrUrl", "value": "http://127.0.0.1:9696"},
                            {"name": "baseUrl", "value": f"http://127.0.0.1:{ports[app]}"},
                            {"name": "apiKey", "value": app_cfg.api_key}
                        ],
                        "syncLevel": "fullSync"
                    })

    async def _provision_overseerr(self):
        # Overseerr doesn't have a simple API key until initialized
        # We might need to inject settings into its database directly or skip for now
        pass

    async def _provision_sabnzbd(self):
        adapter = self.adapters["sabnzbd"]
        api_key = settings.config.services["sabnzbd"].api_key
        url = settings.config.services["sabnzbd"].url
        
        async with aiohttp.ClientSession() as session:
            # Set default download paths
            await session.get(f"{url}/api?mode=set_config&name=download_dir&value=/downloads/incomplete&apikey={api_key}")
            await session.get(f"{url}/api?mode=set_config&name=complete_dir&value=/downloads/complete&apikey={api_key}")

provisioner = None # Initialized in main.py
