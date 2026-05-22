import yaml
import os
import xml.etree.ElementTree as ET
import configparser
from pydantic import BaseModel
from typing import Dict, Optional


class ServiceConfig(BaseModel):
    enabled: bool = False
    api_key: Optional[str] = None
    url: Optional[str] = None


class NexusConfig(BaseModel):
    services: Dict[str, ServiceConfig] = {}


class Settings:
    def __init__(self, config_path: str = "/config/nexus.yml"):
        self.config_path = config_path
        self.config = self.load_config()

    def load_config(self) -> NexusConfig:
        if not os.path.exists(self.config_path):
            return NexusConfig()

        try:
            with open(self.config_path, 'r') as f:
                data = yaml.safe_load(f)
                if data:
                    return NexusConfig(**data)
                return NexusConfig()
        except Exception as e:
            print(f"[Nexus] Error loading config: {e}")
            return NexusConfig()

    def save_config(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config.dict(), f, default_flow_style=False)

    def discover_keys(self):
        """Scans service config files on disk to automatically discover API keys."""
        base_path = "/config"
        ports = {
            "sonarr": 8989,
            "radarr": 7878,
            "lidarr": 8686,
            "whisparr": 6969,
            "prowlarr": 9696,
        }

        # Arr apps (XML based — they auto-generate config.xml on first start)
        for app in ["sonarr", "radarr", "lidarr", "whisparr", "prowlarr"]:
            xml_path = os.path.join(base_path, app, "config.xml")
            if os.path.exists(xml_path):
                try:
                    tree = ET.parse(xml_path)
                    api_key = tree.findtext("ApiKey")
                    if api_key:
                        if app not in self.config.services:
                            self.config.services[app] = ServiceConfig(enabled=True)
                        self.config.services[app].api_key = api_key
                        if not self.config.services[app].url:
                            self.config.services[app].url = f"http://127.0.0.1:{ports[app]}"
                        print(f"[Nexus] Discovered {app} API key")
                except Exception as e:
                    print(f"[Nexus] Error discovering {app} key: {e}")

        # SABnzbd (INI based)
        sab_ini = os.path.join(base_path, "sabnzbd", "sabnzbd.ini")
        if os.path.exists(sab_ini):
            try:
                config = configparser.ConfigParser()
                config.read(sab_ini)
                api_key = config.get("misc", "api_key", fallback=None)
                if api_key:
                    if "sabnzbd" not in self.config.services:
                        self.config.services["sabnzbd"] = ServiceConfig(enabled=True)
                    self.config.services["sabnzbd"].api_key = api_key
                    if not self.config.services["sabnzbd"].url:
                        self.config.services["sabnzbd"].url = "http://127.0.0.1:8092"
                    print("[Nexus] Discovered SABnzbd API key")
            except Exception as e:
                print(f"[Nexus] Error discovering sabnzbd key: {e}")

        # qBittorrent doesn't use API keys — just needs to be marked enabled
        qbt_conf = os.path.join(base_path, "qbittorrent", "qBittorrent", "config", "qBittorrent.conf")
        if os.path.exists(qbt_conf):
            if "qbittorrent" not in self.config.services:
                self.config.services["qbittorrent"] = ServiceConfig(enabled=True)
            if not self.config.services["qbittorrent"].url:
                self.config.services["qbittorrent"].url = "http://127.0.0.1:8091"
            print("[Nexus] Discovered qBittorrent config")

        self.save_config()


settings = Settings()
# Run discovery on startup
settings.discover_keys()
