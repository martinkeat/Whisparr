import yaml
import os
from pydantic import BaseModel
from typing import Dict, Any, Optional

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
                return NexusConfig(**data)
        except Exception:
            return NexusConfig()

    def save_config(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config.dict(), f)

    def discover_keys(self):
        """Scans service config files on disk to automatically discover API keys."""
        base_path = "/config"
        
        # Arr apps (XML based)
        arr_apps = ["sonarr", "radarr", "lidarr", "whisparr", "prowlarr"]
        for app in arr_apps:
            xml_path = os.path.join(base_path, app, "config.xml")
            if os.path.exists(xml_path):
                try:
                    import xml.etree.ElementTree as ET
                    tree = ET.parse(xml_path)
                    api_key = tree.findtext("ApiKey")
                    if api_key:
                        if app not in self.config.services:
                            self.config.services[app] = ServiceConfig(enabled=True)
                        self.config.services[app].api_key = api_key
                        # Set default internal URL if not set
                        ports = {"sonarr": 8989, "radarr": 7878, "lidarr": 8686, "whisparr": 6969, "prowlarr": 9696}
                        if not self.config.services[app].url:
                            self.config.services[app].url = f"http://127.0.0.1:{ports[app]}"
                except Exception as e:
                    print(f"Error discovering {app} key: {e}")

        # SABnzbd (INI based)
        sab_ini = os.path.join(base_path, "sabnzbd", "sabnzbd.ini")
        if os.path.exists(sab_ini):
            try:
                import configparser
                config = configparser.ConfigParser()
                config.read(sab_ini)
                api_key = config.get("misc", "api_key", fallback=None)
                if api_key:
                    if "sabnzbd" not in self.config.services:
                        self.config.services["sabnzbd"] = ServiceConfig(enabled=True)
                    self.config.services["sabnzbd"].api_key = api_key
                    if not self.config.services["sabnzbd"].url:
                        self.config.services["sabnzbd"].url = "http://127.0.0.1:8081"
            except Exception as e:
                print(f"Error discovering sabnzbd key: {e}")

        # qBittorrent
        if "qbittorrent" not in self.config.services:
            self.config.services["qbittorrent"] = ServiceConfig(enabled=True)
            self.config.services["qbittorrent"].url = "http://127.0.0.1:8091"

        self.save_config()

settings = Settings()
# Run discovery on startup
settings.discover_keys()
