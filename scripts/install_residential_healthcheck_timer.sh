#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"
INTERVAL="${INTERVAL:-5min}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "error: run as root on the VPS" >&2
  exit 1
fi

if [[ ! -f "$REPO_DIR/scripts/residential_healthcheck.py" ]]; then
  echo "error: residential_healthcheck.py not found under $REPO_DIR/scripts" >&2
  exit 1
fi

cat >/etc/systemd/system/linkray-residential-healthcheck.service <<EOF
[Unit]
Description=LinkRay residential outbound healthcheck
After=network-online.target x-ui.service
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=$PYTHON_BIN $REPO_DIR/scripts/residential_healthcheck.py --mode auto --restart
EOF

cat >/etc/systemd/system/linkray-residential-healthcheck.timer <<EOF
[Unit]
Description=Run LinkRay residential outbound healthcheck

[Timer]
OnBootSec=2min
OnUnitActiveSec=$INTERVAL
Unit=linkray-residential-healthcheck.service

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now linkray-residential-healthcheck.timer
systemctl list-timers --all linkray-residential-healthcheck.timer
