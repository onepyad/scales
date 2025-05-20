## Deployment on Raspberry Pi 3

This section provides a step-by-step guide for installing and running the project on a Raspberry Pi 3.

### 1. Prepare the system
1. Update packages:
   ```bash
   sudo apt update && sudo apt upgrade
   ```
2. Create a user `scales` with password `!QAZxsw2` (replace with your own if needed):
   ```bash
   sudo adduser scales
   sudo usermod -aG sudo scales   # optional
   ```

### 2. Install Python dependencies
1. Install Python and tools:
   ```bash
   sudo apt install python3 python3-venv python3-pip -y
   ```
2. Create a virtual environment and install requirements:
   ```bash
   python3 -m venv /home/scales/venv
   source /home/scales/venv/bin/activate
   pip install -r requirements.txt
   ```

### 3. Place scripts and create log directory
1. Copy scripts to `/usr/sbin/wsh` and set permissions:
   ```bash
   sudo mkdir -p /usr/sbin/wsh
   sudo cp usr/sbin/wsh/*.py /usr/sbin/wsh/
   sudo chown -R scales:scales /usr/sbin/wsh
   sudo chmod 755 /usr/sbin/wsh/*.py
   ```
2. Create a directory for logs:
   ```bash
   sudo mkdir -p /home/scales/logs
   sudo chown -R scales:scales /home/scales/logs
   ```

### 4. Configure systemd services
1. Copy unit files:
   ```bash
   sudo cp etc/systemd/system/api_service.service /etc/systemd/system/
   sudo cp etc/systemd/system/weith_service.service /etc/systemd/system/
   ```
2. Reload systemd and enable services:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable api_service.service
   sudo systemctl enable weith_service.service
   sudo systemctl start api_service.service
   sudo systemctl start weith_service.service
   ```

### 5. Service management
View logs in real time:
```bash
sudo journalctl -u api_service.service -f
sudo journalctl -u weith_service.service -f
```
Start/stop or restart services:
```bash
sudo systemctl stop api_service.service
sudo systemctl restart api_service.service
sudo systemctl status api_service.service

sudo systemctl stop weith_service.service
sudo systemctl restart weith_service.service
sudo systemctl status weith_service.service
```

### 6. Working with the API
The API listens on port 5000 of the Raspberry Pi.
Examples using `curl`:
```bash
# Get current data
curl http://<PI_IP>:5000/get_data

# Request a new measurement
curl -X POST http://<PI_IP>:5000/make_measurement

# Restart the measurement service
curl -X POST http://<PI_IP>:5000/restart_service
```

### 7. Работа с API в PowerShell

API доступен на порту 5000 Raspberry Pi.

Примеры запросов с помощью PowerShell:

```powershell
# Получить текущие данные
Invoke-RestMethod -Uri "http://<PI_IP>:5000/get_data"

# Запросить новое измерение
Invoke-RestMethod -Method Post -Uri "http://<PI_IP>:5000/make_measurement"

# Перезапустить сервис измерений
Invoke-RestMethod -Method Post -Uri "http://<PI_IP>:5000/restart_service"
```

`weith.py` writes two rotating log files in `/home/scales/logs`:
- `weith_service.log`
- `weith_service_data.log`
