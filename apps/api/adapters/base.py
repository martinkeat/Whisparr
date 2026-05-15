from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Any

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    STARTING = "starting"
    STOPPED = "stopped"
    DISABLED = "disabled"
    WARNING = "warning"
    ERROR = "error"
    UNCONFIGURED = "unconfigured"

class ServiceAdapter(ABC):
    def __init__(self, name: str, internal_url: str):
        self.name = name
        self.internal_url = internal_url

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        pass

    @abstractmethod
    async def version(self) -> Optional[str]:
        pass

    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def collect_logs(self, lines: int = 100) -> List[str]:
        pass

    async def start(self) -> bool:
        import subprocess
        try:
            # s6-rc -u change <service>
            subprocess.run(["/command/s6-rc", "-u", "change", self.name], check=True)
            return True
        except Exception as e:
            print(f"Error starting {self.name}: {e}")
            return False

    async def stop(self) -> bool:
        import subprocess
        try:
            # s6-rc -d change <service>
            subprocess.run(["/command/s6-rc", "-d", "change", self.name], check=True)
            return True
        except Exception as e:
            print(f"Error stopping {self.name}: {e}")
            return False

    async def restart(self) -> bool:
        import subprocess
        try:
            # s6-svc -r /run/service/<service>
            subprocess.run(["/command/s6-svc", "-r", f"/run/service/{self.name}"], check=True)
            return True
        except Exception as e:
            print(f"Error restarting {self.name}: {e}")
            return False
