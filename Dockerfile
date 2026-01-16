# RoXX - Dockerfile
FROM python:3.11-slim-bookworm

# Metadata
LABEL maintainer="Thomas Sautier"
LABEL description="RoXX - RADIUS Authentication Proxy"
LABEL version="1.0-beta"

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    ROXX_CONFIG_DIR=/etc/roxx \
    ROXX_DATA_DIR=/var/lib/roxx

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
# 8000/tcp: Web Console (Future)
EXPOSE 1812/udp 1813/udp 8000/tcp

# Entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["roxx-console"]
