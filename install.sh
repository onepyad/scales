#!/bin/bash
set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root" >&2
  exit 1
fi

# Create user if it doesn't exist
if ! id -u scales >/dev/null 2>&1; then
  useradd -m -s /bin/bash scales
fi

apt update
apt install -y python3 python3-venv python3-pip

# Setup virtual environment
if [ ! -d /home/scales/venv ]; then
  python3 -m venv /home/scales/venv
  chown -R scales:scales /home/scales/venv
fi
sudo -u scales /home/scales/venv/bin/pip install -r requirements.txt

# Install scripts
install -d /usr/sbin/wsh
install -m 755 usr/sbin/wsh/*.py /usr/sbin/wsh/
chown -R scales:scales /usr/sbin/wsh

# Log directory
mkdir -p /home/scales/logs
chown -R scales:scales /home/scales/logs

# Install service files
install -m 644 etc/systemd/system/*.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable api_service.service weith_service.service lcd_display.service
systemctl restart api_service.service weith_service.service lcd_display.service

