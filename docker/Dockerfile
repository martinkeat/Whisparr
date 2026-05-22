# ============================================================
# Nexus — Single-container media automation platform
# ============================================================

# Stage 1: Pull pre-built Whisparr v3 (eros) from hotio image
# This avoids compiling the entire .NET solution and NuGet timeout issues.
FROM ghcr.io/hotio/whisparr:nightly AS whisparr-source

# Stage 2: Pull Overseerr from the official image
FROM sctx/overseerr:latest AS overseerr-source

# Stage 3: Final Image
FROM ubuntu:24.04

LABEL maintainer="spontaneocus"
LABEL description="Nexus - Single-container media automation platform"

# Environment Variables
ENV PUID=99 \
    PGID=100 \
    TZ=Etc/UTC \
    UMASK=022 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    NODE_ENV=production

# Install Base Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    curl \
    ca-certificates \
    python3 \
    python3-pip \
    python3-venv \
    nodejs \
    npm \
    xz-utils \
    tzdata \
    libicu74 \
    libkrb5-3 \
    libssl3 \
    libstdc++6 \
    zlib1g \
    ffmpeg \
    qbittorrent-nox \
    par2 \
    7zip \
    gcc \
    python3-dev \
    libffi-dev \
    libssl-dev \
    libxml2 \
    libxslt1.1 \
    sqlite3 \
    # FlareSolverr / Chromium dependencies
    xvfb \
    libnss3 \
    libnspr4 \
    libatk1.0-0t64 \
    libatk-bridge2.0-0t64 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2t64 \
    && rm -rf /var/lib/apt/lists/*

# Install .NET 6.0 Runtime (required for Whisparr v3 — EOL on Ubuntu 24.04 so use install script)
RUN curl -fsSL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh && \
    chmod +x /tmp/dotnet-install.sh && \
    /tmp/dotnet-install.sh --channel 6.0 --runtime aspnetcore --install-dir /usr/share/dotnet && \
    ln -sf /usr/share/dotnet/dotnet /usr/bin/dotnet && \
    rm /tmp/dotnet-install.sh

# Install s6-overlay
RUN curl -L https://github.com/just-containers/s6-overlay/releases/download/v3.1.6.2/s6-overlay-noarch.tar.xz -o /tmp/s6-noarch.tar.xz && \
    curl -L https://github.com/just-containers/s6-overlay/releases/download/v3.1.6.2/s6-overlay-x86_64.tar.xz -o /tmp/s6-x86_64.tar.xz && \
    tar -C / -Jxpf /tmp/s6-noarch.tar.xz && \
    tar -C / -Jxpf /tmp/s6-x86_64.tar.xz && \
    rm /tmp/s6-noarch.tar.xz /tmp/s6-x86_64.tar.xz

# Set up virtual environment for Python services
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Install SABnzbd from source
RUN mkdir -p /opt/sabnzbd && \
    curl -L "https://github.com/sabnzbd/sabnzbd/releases/download/4.3.2/SABnzbd-4.3.2-src.tar.gz" -o /tmp/sabnzbd.tar.gz && \
    tar -xzf /tmp/sabnzbd.tar.gz -C /opt/sabnzbd --strip-components=1 && \
    rm /tmp/sabnzbd.tar.gz && \
    /app/venv/bin/pip install --no-cache-dir -r /opt/sabnzbd/requirements.txt

# ---- Arr Suite ----

# Sonarr
RUN curl -L "https://services.sonarr.tv/v1/download/main/latest?version=4&os=linux&arch=x64" -o /tmp/sonarr.tar.gz && \
    tar -xzf /tmp/sonarr.tar.gz -C /opt && \
    rm /tmp/sonarr.tar.gz

# Radarr
RUN curl -L "https://radarr.servarr.com/v1/update/master/updatefile?os=linux&runtime=netcore&arch=x64" -o /tmp/radarr.tar.gz && \
    tar -xzf /tmp/radarr.tar.gz -C /opt && \
    rm /tmp/radarr.tar.gz

# Lidarr
RUN curl -L "https://lidarr.servarr.com/v1/update/master/updatefile?os=linux&runtime=netcore&arch=x64" -o /tmp/lidarr.tar.gz && \
    tar -xzf /tmp/lidarr.tar.gz -C /opt && \
    rm /tmp/lidarr.tar.gz

# Prowlarr
RUN curl -L "https://prowlarr.servarr.com/v1/update/master/updatefile?os=linux&runtime=netcore&arch=x64" -o /tmp/prowlarr.tar.gz && \
    tar -xzf /tmp/prowlarr.tar.gz -C /opt && \
    rm /tmp/prowlarr.tar.gz

# FlareSolverr
RUN mkdir -p /opt/FlareSolverr && \
    curl -L "https://github.com/FlareSolverr/FlareSolverr/releases/download/v3.3.21/flaresolverr_linux_x64.tar.gz" -o /tmp/flaresolverr.tar.gz && \
    tar -xzf /tmp/flaresolverr.tar.gz -C /opt/FlareSolverr --strip-components=1 && \
    rm /tmp/flaresolverr.tar.gz

# Whisparr v3 (eros) — pre-built from hotio image
COPY --from=whisparr-source /app /opt/Whisparr
RUN chmod +x /opt/Whisparr/Whisparr || true

# Overseerr — pre-built from official image
COPY --from=overseerr-source /app /opt/Overseerr

# ---- Directory Structure ----
RUN mkdir -p \
    /app/api \
    /app/web \
    /app/worker \
    /app/transcoder \
    /config \
    /downloads/incomplete \
    /downloads/complete \
    /tv \
    /movies \
    /music \
    /adult \
    /transcode

# ---- Application Code ----
COPY apps/web /app/web
COPY branding /app/branding
COPY apps/api /app/api
COPY apps/worker /app/worker
COPY apps/transcoder /app/transcoder

# Install API dependencies
RUN /app/venv/bin/pip install --no-cache-dir fastapi uvicorn pydantic pyyaml aiohttp

# Copy Docker rootfs (s6-overlay service definitions)
COPY docker/rootfs /

# ---- Ports ----
# Nexus Dashboard / API
EXPOSE 8080
# BitTorrent
EXPOSE 6881/tcp
EXPOSE 6881/udp

ENTRYPOINT ["/init"]
