#!/bin/sh
set -eu

SOURCE="${1:?Usage: upgrade_linux.sh /path/to/new/roxx [target]}"
TARGET="${2:-/usr/bin/roxx}"
BACKUP_DIR="${ROXX_ROLLBACK_DIR:-/var/lib/roxx/rollback}"
SERVICE="${ROXX_SERVICE_NAME:-roxx.service}"

if [ "$(id -u)" -ne 0 ]; then
    echo "Upgrade requires root privileges." >&2
    exit 1
fi
if [ ! -f "$SOURCE" ]; then
    echo "Upgrade source does not exist: $SOURCE" >&2
    exit 1
fi

mkdir -p "$BACKUP_DIR"
BACKUP="$BACKUP_DIR/roxx-$(date -u +%Y%m%dT%H%M%SZ)"
if [ -f "$TARGET" ]; then
    cp -p "$TARGET" "$BACKUP"
fi

rollback() {
    echo "Readiness check failed; rolling back." >&2
    if [ -f "$BACKUP" ]; then
        install -m 0755 "$BACKUP" "$TARGET"
        systemctl restart "$SERVICE"
    fi
    journalctl -u "$SERVICE" -n 100 --no-pager >&2 || true
    exit 1
}

systemctl stop "$SERVICE"
install -m 0755 "$SOURCE" "$TARGET"
systemctl start "$SERVICE"

attempt=0
while [ "$attempt" -lt 30 ]; do
    if curl --fail --silent --show-error --insecure https://127.0.0.1:8000/readyz >/dev/null 2>&1 || \
       curl --fail --silent --show-error http://127.0.0.1:8000/readyz >/dev/null 2>&1; then
        echo "RoXX upgrade completed; rollback binary: $BACKUP"
        exit 0
    fi
    attempt=$((attempt + 1))
    sleep 1
done
rollback
