#!/bin/sh
set -eu

if ! getent group roxx >/dev/null 2>&1; then
    groupadd --system roxx
fi
if ! getent passwd roxx >/dev/null 2>&1; then
    useradd --system --gid roxx --home-dir /var/lib/roxx --shell /usr/sbin/nologin roxx
fi
install -d -o roxx -g roxx -m 0750 /etc/roxx /var/lib/roxx /var/log/roxx
if command -v systemctl >/dev/null 2>&1; then
    systemctl daemon-reload
    systemctl enable roxx.service
fi
