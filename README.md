# Развертывание на Raspberry Pi 3

Пошаговое руководство для установки и запуска проекта на Raspberry Pi 3.
Для автоматической установки можно выполнить `sudo ./install.sh` в каталоге проекта.

---

## Структура проекта

```
.
├── install.sh                       # автоматический установщик
├── requirements.txt                 # python-зависимости
├── etc/systemd/system/
│   ├── api_service.service          # Flask API на порту 5000
│   ├── weith_service.service        # цикл измерения весов и лазеров
│   ├── lcd_display.service          # вывод значений на LCD 20x4
│   └── key_service.service          # обработчик GPIO-кнопки
└── usr/sbin/wsh/
    ├── api.py                       # Flask API
    ├── weith.py                     # опрос весов и лазеров (UART/USB)
    ├── lcd_display.py               # клиент LCD (RPLCD/PCF8574)
    ├── key_listener.py              # слушает кнопку на GPIO 17
    └── usbkey.sh                    # вызывается key_listener при нажатии
```

---

## 0. Скачивание файлов с GitHub

```bash
git clone https://github.com/onepyad/scales.git
cd scales
```

Если `git` не установлен: `sudo apt install git -y`.

---

## 1. Подготовка системы

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip python3-smbus i2c-tools curl
```

Включите I2C (нужно для LCD):
```bash
sudo raspi-config nonint do_i2c 0
# или интерактивно: sudo raspi-config → Interface Options → I2C → Enable
```

Создайте пользователя `scales`:
```bash
sudo adduser scales
# при необходимости — sudo usermod -aG sudo scales
```

---

## 2. Виртуальные окружения и зависимости

В проекте используются два venv:
* `/home/scales/venv` — для `api.py`, `weith.py`, `key_listener.py`;
* `/usr/sbin/wsh/.venv` — для `lcd_display.py` (так настроено в `lcd_display.service`).

```bash
cd ~/scales
sudo -u scales python3 -m venv /home/scales/venv
sudo -u scales /home/scales/venv/bin/pip install --upgrade pip
sudo -u scales /home/scales/venv/bin/pip install -r requirements.txt
```

---

## 3. Размещение скриптов и логов

```bash
cd ~/scales
sudo mkdir -p /usr/sbin/wsh
sudo cp usr/sbin/wsh/*.py usr/sbin/wsh/*.sh /usr/sbin/wsh/
sudo chown -R scales:scales /usr/sbin/wsh
sudo chmod 755 /usr/sbin/wsh/*.py /usr/sbin/wsh/*.sh

# venv для lcd_display
sudo -u scales python3 -m venv /usr/sbin/wsh/.venv
sudo -u scales /usr/sbin/wsh/.venv/bin/pip install --upgrade pip
sudo -u scales /usr/sbin/wsh/.venv/bin/pip install -r requirements.txt

# каталог для логов
sudo mkdir -p /home/scales/logs
sudo chown -R scales:scales /home/scales/logs
```

---

## 4. Настройка systemd

```bash
cd ~/scales
sudo cp etc/systemd/system/api_service.service   /etc/systemd/system/
sudo cp etc/systemd/system/weith_service.service /etc/systemd/system/
sudo cp etc/systemd/system/lcd_display.service   /etc/systemd/system/
sudo cp etc/systemd/system/key_service.service   /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable api_service.service weith_service.service lcd_display.service key_service.service
sudo systemctl start  api_service.service weith_service.service lcd_display.service key_service.service
```

---

## 5. Управление сервисами

Просмотр логов:
```bash
sudo journalctl -u api_service.service   -f
sudo journalctl -u weith_service.service -f
sudo journalctl -u lcd_display.service   -f
sudo journalctl -u key_service.service   -f
```

Управление:
```bash
sudo systemctl status   <unit>
sudo systemctl restart  <unit>
sudo systemctl stop     <unit>
```

---

## 6. API через `curl`

API доступен на порту **5000**:
```bash
# Получить последние данные
curl http://<PI_IP>:5000/get_data

# Запустить новое измерение
curl -X POST http://<PI_IP>:5000/make_measurement

# Перезапустить weith_service
curl -X POST http://<PI_IP>:5000/restart_service
```

---

## 7. API через PowerShell

```powershell
Invoke-RestMethod -Uri "http://<PI_IP>:5000/get_data"
Invoke-RestMethod -Method Post -Uri "http://<PI_IP>:5000/make_measurement"
Invoke-RestMethod -Method Post -Uri "http://<PI_IP>:5000/restart_service"
```

---

## 8. Логирование

Логи пишутся в `/home/scales/logs`:
- `weith_service.log` — основной лог сервиса измерений;
- `weith_service_data.log` — измеренные значения;
- `key_listener.log` — нажатия GPIO-кнопки.

Сервисы также пишут в `journalctl`.

---

## 9. Логика работы с 1С

В интерфейсе 1С есть кнопка «Сделать измерение»:
- 1С шлёт `POST /make_measurement` на API;
- API создаёт флаг `/tmp/do_measure.flag`;
- `weith.py` видит флаг, опрашивает весы и лазеры, отправляет данные `POST /update_data`;
- 1С через несколько секунд делает `GET /get_data` и подставляет данные в таблицу.

Параллельно физическая кнопка на GPIO 17 (через `key_listener.py` → `usbkey.sh`) делает тот же `POST /make_measurement`.

---
