import asyncio
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn

from adapters.qbittorrent import QBittorrentAdapter
from adapters.sabnzbd import SABnzbdAdapter
from adapters.arr import SonarrAdapter, RadarrAdapter, LidarrAdapter, ProwlarrAdapter, WhisparrAdapter
from adapters.overseerr import OverseerrAdapter
from adapters.flaresolverr import FlareSolverrAdapter
from adapters.transcoder import TranscoderAdapter

app = FastAPI(title="Nexus API", version="0.1.0")

from core.settings import settings

adapters = {
    "qbittorrent": QBittorrentAdapter(),
    "sabnzbd": SABnzbdAdapter(),
    "sonarr": SonarrAdapter(),
    "radarr": RadarrAdapter(),
    "lidarr": LidarrAdapter(),
    "whisparr": WhisparrAdapter(),
    "prowlarr": ProwlarrAdapter(),
    "overseerr": OverseerrAdapter(),
    "flaresolverr": FlareSolverrAdapter(),
    "transcoder": TranscoderAdapter()
}

# Initialize with saved settings
for name, adapter in adapters.items():
    if name in settings.config.services:
        cfg = settings.config.services[name]
        if hasattr(adapter, 'api_key'):
            adapter.api_key = cfg.api_key
        if hasattr(adapter, 'internal_url') and cfg.url:
            adapter.internal_url = cfg.url


@app.on_event("startup")
async def startup_event():
    """Run key discovery and provisioning on startup."""
    # Give services a moment to generate their config files on first boot
    await asyncio.sleep(5)
    settings.discover_keys()
    # Re-apply discovered keys to adapters
    for name, adapter in adapters.items():
        if name in settings.config.services:
            cfg = settings.config.services[name]
            if hasattr(adapter, 'api_key') and cfg.api_key:
                adapter.api_key = cfg.api_key
            if hasattr(adapter, 'internal_url') and cfg.url:
                adapter.internal_url = cfg.url


@app.post("/api/services/{service_name}/restart")
async def restart_service(service_name: str):
    if service_name not in adapters:
        return {"error": "Service not found"}, 404
    adapter = adapters[service_name]
    success = await adapter.restart()
    if success:
        return {"message": f"Restart request sent for {service_name}"}
    return {"error": f"Failed to restart {service_name}"}, 500


@app.get("/api/settings")
async def get_settings():
    from core.settings import settings
    return settings.config.dict()


@app.put("/api/settings")
async def update_settings(new_settings: dict):
    from core.settings import settings, ServiceConfig

    if "services" in new_settings:
        for name, config in new_settings["services"].items():
            settings.config.services[name] = ServiceConfig(**config)
            # Update the adapter's API key if it exists
            if name in adapters and hasattr(adapters[name], 'api_key'):
                adapters[name].api_key = config.get("api_key")

    settings.save_config()
    return {"message": "Settings updated"}


@app.post("/api/settings/toggle")
async def toggle_service(data: dict):
    from core.settings import settings
    name = data.get("name")
    enabled = data.get("enabled")

    if name not in settings.config.services:
        from core.settings import ServiceConfig
        settings.config.services[name] = ServiceConfig(enabled=enabled)
    else:
        settings.config.services[name].enabled = enabled

    settings.save_config()

    # Control service via s6-rc
    adapter = adapters.get(name)
    if adapter:
        if enabled:
            await adapter.start()
            # Wait for service to start and generate config, then provision
            from core.provisioner import provisioner
            asyncio.create_task(provisioner.provision_service(name))
        else:
            await adapter.stop()

    return {"message": f"Service {name} {'enabled' if enabled else 'disabled'}"}


@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "nexus-api"}


@app.get("/api/status")
async def status():
    from core.settings import settings
    service_status = {}
    for name, adapter in adapters.items():
        if name in settings.config.services and settings.config.services[name].enabled:
            try:
                service_status[name] = await adapter.get_status()
            except Exception:
                service_status[name] = {"name": name, "health": "error"}
        else:
            service_status[name] = {"name": name, "health": "disabled"}

    # Pull real stats from enabled Arr services
    stats = {
        "total_movies": 0,
        "total_episodes": 0,
        "active_downloads": 0,
        "disk_free": "N/A"
    }

    # Fetch stats concurrently
    tasks = []
    
    if "radarr" in service_status and service_status["radarr"]["health"] == "healthy":
        tasks.append(adapters["radarr"].get_movie_count())
    else:
        tasks.append(asyncio.sleep(0, result=0))

    if "sonarr" in service_status and service_status["sonarr"]["health"] == "healthy":
        tasks.append(adapters["sonarr"].get_episode_count())
    else:
        tasks.append(asyncio.sleep(0, result=0))

    if "qbittorrent" in service_status and service_status["qbittorrent"]["health"] == "healthy":
        tasks.append(adapters["qbittorrent"].get_active_downloads())
    else:
        tasks.append(asyncio.sleep(0, result=0))

    if "sabnzbd" in service_status and service_status["sabnzbd"]["health"] == "healthy":
        tasks.append(adapters["sabnzbd"].get_active_downloads())
    else:
        tasks.append(asyncio.sleep(0, result=0))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    stats["total_movies"] = results[0] if isinstance(results[0], int) else 0
    stats["total_episodes"] = results[1] if isinstance(results[1], int) else 0
    
    qbit_dl = results[2] if isinstance(results[2], int) else 0
    sab_dl = results[3] if isinstance(results[3], int) else 0
    stats["active_downloads"] = qbit_dl + sab_dl


    # Try to get disk free space
    try:
        statvfs = os.statvfs('/config')
        free_bytes = statvfs.f_bavail * statvfs.f_frsize
        free_tb = free_bytes / (1024**4)
        if free_tb >= 1:
            stats["disk_free"] = f"{free_tb:.1f} TB"
        else:
            free_gb = free_bytes / (1024**3)
            stats["disk_free"] = f"{free_gb:.0f} GB"
    except Exception:
        pass

    return {
        "nexus": "healthy",
        "services": service_status,
        "stats": stats
    }


from core.provisioner import Provisioner
import core.provisioner as p_mod
p_mod.provisioner = Provisioner(adapters)

# Mount branding
if os.path.exists("/app/branding"):
    app.mount("/branding", StaticFiles(directory="/app/branding"), name="branding")
elif os.path.exists("../../branding"):
    app.mount("/branding", StaticFiles(directory="../../branding"), name="branding")

# Mount web frontend last (as catch-all for /)
if os.path.exists("/app/web"):
    app.mount("/", StaticFiles(directory="/app/web", html=True), name="web")
elif os.path.exists("../web"):
    app.mount("/", StaticFiles(directory="../web", html=True), name="web")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
