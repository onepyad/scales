#!/bin/bash
# install.sh: automate installation of the scales project
# This script must be run as root.
set -e

if [ "$(id -u)" -ne 0 ]; then
    echo "Please run as root" >&2
    exit 1
fi

# Update system and install python
apt update && apt upgrade -y
apt install -y python3 python3-venv python3-pip

# Create scales user if it does not exist
if ! id scales >/dev/null 2>&1; then
    useradd -m -s /bin/bash scales
    echo 'scales:!QAZxsw2' | chpasswd
    # Uncomment the next line if you want the user in the sudo group
    # usermod -aG sudo scales
fi

# Set up virtual environment and install Python dependencies
sudo -u scales python3 -m venv /home/scales/venv
sudo -u scales /home/scales/venv/bin/pip install --upgrade pip
sudo -u scales /home/scales/venv/bin/pip install -r requirements.txt

# Copy application scripts
mkdir -p /usr/sbin/wsh
cp usr/sbin/wsh/*.py /usr/sbin/wsh/
chown -R scales:scales /usr/sbin/wsh
chmod 755 /usr/sbin/wsh/*.py

# Create log directory
mkdir -p /home/scales/logs
chown -R scales:scales /home/scales/logs

# Install systemd services
cp etc/systemd/system/api_service.service /etc/systemd/system/
cp etc/systemd/system/weith_service.service /etc/systemd/system/
cp etc/systemd/system/lcd_display.service /etc/systemd/system/

systemctl daemon-reload
systemctl enable api_service.service weith_service.service lcd_display.service
systemctl start api_service.service weith_service.service lcd_display.service

echo "Installation complete."
