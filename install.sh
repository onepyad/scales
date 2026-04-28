#!/bin/bash
# install.sh: автоматическая установка проекта scales на Raspberry Pi.
# Запускать от root: sudo ./install.sh
set -e

if [ "$(id -u)" -ne 0 ]; then
    echo "Запустите скрипт от root (sudo)" >&2
    exit 1
fi

# Обновление системы и установка пакетов
apt update && apt upgrade -y
apt install -y python3 python3-venv python3-pip python3-smbus i2c-tools curl

# Включение I2C на Raspberry Pi (если raspi-config доступен)
if command -v raspi-config >/dev/null 2>&1; then
    raspi-config nonint do_i2c 0 || true
fi

# Создание пользователя scales (без пароля; задайте через `passwd scales` при необходимости)
if ! id scales >/dev/null 2>&1; then
    useradd -m -s /bin/bash scales
fi

# Основной venv для api/weith/key_listener
sudo -u scales python3 -m venv /home/scales/venv
sudo -u scales /home/scales/venv/bin/pip install --upgrade pip
sudo -u scales /home/scales/venv/bin/pip install -r requirements.txt

# Копирование скриптов
mkdir -p /usr/sbin/wsh
cp usr/sbin/wsh/api.py            /usr/sbin/wsh/
cp usr/sbin/wsh/weith.py          /usr/sbin/wsh/
cp usr/sbin/wsh/lcd_display.py    /usr/sbin/wsh/
cp usr/sbin/wsh/key_listener.py   /usr/sbin/wsh/
cp usr/sbin/wsh/usbkey.sh         /usr/sbin/wsh/
chown -R scales:scales /usr/sbin/wsh
chmod 755 /usr/sbin/wsh/*.py /usr/sbin/wsh/*.sh

# Отдельный venv для lcd_display (так настроено в lcd_display.service)
sudo -u scales python3 -m venv /usr/sbin/wsh/.venv
sudo -u scales /usr/sbin/wsh/.venv/bin/pip install --upgrade pip
sudo -u scales /usr/sbin/wsh/.venv/bin/pip install -r requirements.txt

# Каталог для логов
mkdir -p /home/scales/logs
chown -R scales:scales /home/scales/logs

# Установка systemd-юнитов
cp etc/systemd/system/api_service.service   /etc/systemd/system/
cp etc/systemd/system/weith_service.service /etc/systemd/system/
cp etc/systemd/system/lcd_display.service   /etc/systemd/system/
cp etc/systemd/system/key_service.service   /etc/systemd/system/

systemctl daemon-reload
systemctl enable api_service.service weith_service.service lcd_display.service key_service.service
systemctl start  api_service.service weith_service.service lcd_display.service key_service.service

echo "Установка завершена. Если включали I2C — может потребоваться перезагрузка."
