# Stage 1: Build Web Frontend
# We use the local source directly in the final stage for now
# unless a real build step (like npm build) is added later.

# Stage 2: Build Whisparr
FROM mcr.microsoft.com/dotnet/sdk:9.0 AS whisparr-build
WORKDIR /src
RUN apt-get update && apt-get install -y git && \
    git clone https://github.com/Whisparr/Whisparr.git . && \
    git checkout eros && \
    cd src && dotnet restore Whisparr.sln && dotnet build Whisparr.sln -c Release --no-restore

# Stage 3: Overseerr Source
FROM sctx/overseerr:latest AS overseerr-source

# Stage 4: Final Image
FROM ubuntu:24.04

# Metadata
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
RUN apt-get update && apt-get install -y \
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

# Install s6-overlay
RUN curl -L https://github.com/just-containers/s6-overlay/releases/download/v3.1.6.2/s6-overlay-noarch.tar.xz -o /tmp/s6-noarch.tar.xz && \
    curl -L https://github.com/just-containers/s6-overlay/releases/download/v3.1.6.2/s6-overlay-x86_64.tar.xz -o /tmp/s6-x86_64.tar.xz && \
    tar -C / -Jxpf /tmp/s6-noarch.tar.xz && \
    tar -C / -Jxpf /tmp/s6-x86_64.tar.xz && \
    rm /tmp/s6-noarch.tar.xz /tmp/s6-x86_64.tar.xz

# Set up virtual environment early for all Python services
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Install SABnzbd from source
RUN mkdir -p /opt/sabnzbd && \
    curl -L "https://github.com/sabnzbd/sabnzbd/releases/download/4.3.2/SABnzbd-4.3.2-src.tar.gz" -o /tmp/sabnzbd.tar.gz && \
    tar -xzf /tmp/sabnzbd.tar.gz -C /opt/sabnzbd --strip-components=1 && \
    rm /tmp/sabnzbd.tar.gz && \
    /app/venv/bin/pip install --no-cache-dir -r /opt/sabnzbd/requirements.txt

# Install Arr Suite and Indexing tools
RUN mkdir -p /opt

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

# Create directory structure
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

# Copy web frontend
COPY apps/web /app/web

# Copy branding
COPY branding /app/branding

# Copy Whisparr
COPY --from=whisparr-build /src/_output/net6.0 /opt/Whisparr
RUN chmod +x /opt/Whisparr/Whisparr

# Copy Overseerr from source image
# The official image has the app in /app
COPY --from=overseerr-source /app /opt/Overseerr

# Copy Nexus application code
COPY apps/api /app/api
COPY apps/worker /app/worker
COPY apps/transcoder /app/transcoder

# Install API dependencies
RUN /app/venv/bin/pip install --no-cache-dir fastapi uvicorn pydantic pyyaml aiohttp

# Copy Docker rootfs (scripts, s6-overlay configs)
COPY docker/rootfs /

# Expose Nexus GUI/API port
EXPOSE 8080

# BitTorrent ports
EXPOSE 6881/tcp
EXPOSE 6881/udp

ENTRYPOINT ["/init"]
