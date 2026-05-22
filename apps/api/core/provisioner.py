import aiohttp
import asyncio
import os
import xml.etree.ElementTree as ET
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

        # Wait for service to be healthy (up to 60s for first boot)
        for i in range(60):
            try:
                status = await adapter.get_status()
                if status.get('health') == 'healthy':
                    break
            except Exception:
                pass
            await asyncio.sleep(1)
        else:
            print(f"[Nexus] Provisioning timed out for {name}")
            return

        # Re-discover API keys (the service may have just generated its config.xml)
        settings.discover_keys()

        # Re-apply discovered key to the adapter
        if name in settings.config.services:
            cfg = settings.config.services[name]
            if hasattr(adapter, 'api_key') and cfg.api_key:
                adapter.api_key = cfg.api_key

        print(f"[Nexus] Provisioning {name}...")

        try:
            if name in ["sonarr", "radarr", "lidarr", "whisparr"]:
                await self._provision_arr(name)
            elif name == "prowlarr":
                await self._provision_prowlarr()
            elif name == "sabnzbd":
                await self._provision_sabnzbd()
            print(f"[Nexus] Provisioning {name} complete.")
        except Exception as e:
            print(f"[Nexus] Provisioning error for {name}: {e}")

    async def _provision_arr(self, name: str):
        """Configure an Arr app with root folders and download clients."""
        api_key = settings.config.services.get(name, None)
        if not api_key or not api_key.api_key:
            print(f"[Nexus] No API key available for {name}, skipping provisioning")
            return

        api_key_str = api_key.api_key
        url = api_key.url or f"http://127.0.0.1:{self._get_port(name)}"

        async with aiohttp.ClientSession() as session:
            headers = {"X-Api-Key": api_key_str}

            # 1. Set up Root Folders
            root_folders = {
                "sonarr": "/tv",
                "radarr": "/movies",
                "lidarr": "/music",
                "whisparr": "/adult"
            }
            try:
                await session.post(
                    f"{url}/api/v3/rootfolder",
                    headers=headers,
                    json={"path": root_folders.get(name, "/media")},
                    timeout=aiohttp.ClientTimeout(total=10)
                )
            except Exception as e:
                print(f"[Nexus] Root folder setup for {name}: {e}")

            # 2. Set up qBittorrent as download client
            if "qbittorrent" in settings.config.services:
                try:
                    await session.post(
                        f"{url}/api/v3/downloadclient",
                        headers=headers,
                        json={
                            "enable": True,
                            "name": "qBittorrent (Nexus)",
                            "implementation": "QBittorrent",
                            "configContract": "QBittorrentSettings",
                            "protocol": "torrent",
                            "fields": [
                                {"name": "host", "value": "127.0.0.1"},
                                {"name": "port", "value": 8091},
                                {"name": "username", "value": "admin"},
                                {"name": "password", "value": "adminadmin"},
                                {"name": "movieCategory", "value": name},
                                {"name": "tvCategory", "value": name},
                            ]
                        },
                        timeout=aiohttp.ClientTimeout(total=10)
                    )
                except Exception as e:
                    print(f"[Nexus] qBittorrent client setup for {name}: {e}")

            # 3. Set up SABnzbd as download client
            if "sabnzbd" in settings.config.services:
                sab_cfg = settings.config.services.get("sabnzbd")
                if sab_cfg and sab_cfg.api_key:
                    try:
                        await session.post(
                            f"{url}/api/v3/downloadclient",
                            headers=headers,
                            json={
                                "enable": True,
                                "name": "SABnzbd (Nexus)",
                                "implementation": "Sabnzbd",
                                "configContract": "SabnzbdSettings",
                                "protocol": "usenet",
                                "fields": [
                                    {"name": "host", "value": "127.0.0.1"},
                                    {"name": "port", "value": 8092},
                                    {"name": "apiKey", "value": sab_cfg.api_key},
                                    {"name": "tvCategory", "value": name},
                                    {"name": "movieCategory", "value": name},
                                ]
                            },
                            timeout=aiohttp.ClientTimeout(total=10)
                        )
                    except Exception as e:
                        print(f"[Nexus] SABnzbd client setup for {name}: {e}")

    async def _provision_prowlarr(self):
        """Link Prowlarr to all enabled Arr applications."""
        prowlarr_cfg = settings.config.services.get("prowlarr")
        if not prowlarr_cfg or not prowlarr_cfg.api_key:
            print("[Nexus] No Prowlarr API key, skipping sync setup")
            return

        api_key = prowlarr_cfg.api_key
        url = prowlarr_cfg.url or "http://127.0.0.1:9696"

        async with aiohttp.ClientSession() as session:
            headers = {"X-Api-Key": api_key}

            # Link Prowlarr to each enabled Arr app
            apps = ["sonarr", "radarr", "lidarr", "whisparr"]
            impl_map = {
                "sonarr": "Sonarr",
                "radarr": "Radarr",
                "lidarr": "Lidarr",
                "whisparr": "Whisparr",
            }

            for app_name in apps:
                app_cfg = settings.config.services.get(app_name)
                if app_cfg and app_cfg.enabled and app_cfg.api_key:
                    port = self._get_port(app_name)
                    impl = impl_map[app_name]
                    try:
                        await session.post(
                            f"{url}/api/v1/applications",
                            headers=headers,
                            json={
                                "name": impl,
                                "implementation": impl,
                                "configContract": f"{impl}Settings",
                                "fields": [
                                    {"name": "prowlarrUrl", "value": "http://127.0.0.1:9696"},
                                    {"name": "baseUrl", "value": f"http://127.0.0.1:{port}"},
                                    {"name": "apiKey", "value": app_cfg.api_key},
                                ],
                                "syncLevel": "fullSync"
                            },
                            timeout=aiohttp.ClientTimeout(total=10)
                        )
                        print(f"[Nexus] Linked Prowlarr → {impl}")
                    except Exception as e:
                        print(f"[Nexus] Prowlarr → {impl} link error: {e}")

    async def _provision_sabnzbd(self):
        """Configure SABnzbd download paths."""
        sab_cfg = settings.config.services.get("sabnzbd")
        if not sab_cfg or not sab_cfg.api_key:
            return

        api_key = sab_cfg.api_key
        url = sab_cfg.url or "http://127.0.0.1:8092"

        async with aiohttp.ClientSession() as session:
            try:
                await session.get(f"{url}/api?mode=set_config&name=download_dir&value=/downloads/incomplete&apikey={api_key}",
                                  timeout=aiohttp.ClientTimeout(total=10))
                await session.get(f"{url}/api?mode=set_config&name=complete_dir&value=/downloads/complete&apikey={api_key}",
                                  timeout=aiohttp.ClientTimeout(total=10))
                print("[Nexus] SABnzbd download paths configured")
            except Exception as e:
                print(f"[Nexus] SABnzbd config error: {e}")

    @staticmethod
    def _get_port(name: str) -> int:
        ports = {
            "sonarr": 8989,
            "radarr": 7878,
            "lidarr": 8686,
            "whisparr": 6969,
            "prowlarr": 9696,
        }
        return ports.get(name, 8080)


provisioner = None  # Initialized in main.py
