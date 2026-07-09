#!/bin/sh
set -eu

if command -v systemctl >/dev/null 2>&1; then
    systemctl disable --now roxx.service >/dev/null 2>&1 || true
    systemctl daemon-reload
fi
