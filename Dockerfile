# RoXX - Dockerfile
FROM python:3.12-slim-bookworm

# Metadata
LABEL maintainer="Thomas Sautier"
LABEL description="RoXX - RADIUS Authentication Proxy"
LABEL version="1.0.2"

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    ROXX_CONFIG_DIR=/etc/roxx \
    ROXX_DATA_DIR=/var/lib/roxx \
    ROXX_LOG_DIR=/var/log/roxx \
    ROXX_SECURITY_PROFILE=production

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    freeradius \
    freeradius-utils \
    gcc \
    libssl-dev \
    curl \
    nano \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Setup application directory
WORKDIR /app

# Copy project files
COPY . .

# Install Python dependencies and the application
RUN pip install --no-cache-dir .

# Create necessary directories
RUN mkdir -p ${ROXX_CONFIG_DIR} ${ROXX_DATA_DIR} /var/log/roxx

# Expose ports
# 1812/udp: RADIUS Authentication
# 1813/udp: RADIUS Accounting
# 8000/tcp: Web console and API
EXPOSE 1812/udp 1813/udp 8000/tcp

# Entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl --fail --insecure https://127.0.0.1:8000/readyz || exit 1

CMD ["roxx", "server"]
