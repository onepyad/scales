# Развертывание на Raspberry Pi 3

Установка проекта на Raspberry Pi одной командой:

```bash
git clone https://github.com/onepyad/scales.git
cd scales
sudo ./install.sh
```

Скрипт ставит системные пакеты, создаёт пользователя `scales`, разворачивает venv, копирует скрипты, регистрирует и стартует все systemd-юниты.

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

## Что делает `install.sh`

1. `apt install` системных пакетов: `python3`, `python3-venv`, `python3-pip`, `python3-smbus`, `i2c-tools`, `curl`.
2. Включает I2C через `raspi-config nonint do_i2c 0`.
3. Создаёт пользователя `scales` (без пароля; задайте `sudo passwd scales` при необходимости) и добавляет его в группы `gpio`, `i2c`, `dialout`.
4. Создаёт каталоги `/usr/sbin/wsh` (скрипты) и `/home/scales/logs` (логи).
5. Копирует все Python-скрипты и `usbkey.sh` в `/usr/sbin/wsh` с правами `0755` от имени `scales`.
6. Создаёт **один** venv в `/home/scales/venv` и ставит `requirements.txt`.
7. Копирует все 4 systemd-юнита в `/etc/systemd/system`, делает `daemon-reload`, `enable` и `restart` каждого сервиса.

Скрипт идемпотентен — повторный запуск обновит установку.

### Параметры установки

Через переменные окружения:

| Переменная       | По умолчанию          | Описание                     |
|------------------|-----------------------|------------------------------|
| `SCALES_USER`    | `scales`              | системный пользователь       |
| `SCALES_HOME`    | `/home/$SCALES_USER`  | домашний каталог             |
| `SCALES_VENV`    | `$SCALES_HOME/venv`   | путь к venv                  |
| `SCALES_BIN`     | `/usr/sbin/wsh`       | куда копируются скрипты      |
| `SCALES_LOG_DIR` | `$SCALES_HOME/logs`   | каталог для логов            |
| `SCALES_SYSTEMD` | `/etc/systemd/system` | каталог systemd-юнитов       |

Пример: установить в `/opt/scales`:
```bash
sudo SCALES_BIN=/opt/scales SCALES_VENV=/opt/scales/venv ./install.sh
```

При нестандартных путях пути в `[Service] ExecStart=...` подменяются автоматически.

---

## Управление сервисами

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

## API

API доступен на порту **5000**.

`curl`:
```bash
curl http://<PI_IP>:5000/get_data
curl -X POST http://<PI_IP>:5000/make_measurement
curl -X POST http://<PI_IP>:5000/restart_service
```

PowerShell:
```powershell
Invoke-RestMethod -Uri "http://<PI_IP>:5000/get_data"
Invoke-RestMethod -Method Post -Uri "http://<PI_IP>:5000/make_measurement"
Invoke-RestMethod -Method Post -Uri "http://<PI_IP>:5000/restart_service"
```

---

## Логи

Пишутся в `/home/scales/logs`:
- `weith_service.log` — основной лог сервиса измерений;
- `weith_service_data.log` — измеренные значения;
- `key_listener.log` — нажатия GPIO-кнопки.

Сервисы дополнительно пишут в `journalctl`.

---

## Логика работы с 1С

В интерфейсе 1С — кнопка «Сделать измерение»:
- 1С шлёт `POST /make_measurement` на API;
- API создаёт флаг `/tmp/do_measure.flag`;
- `weith.py` видит флаг, опрашивает весы и лазеры, отправляет данные `POST /update_data`;
- 1С через несколько секунд делает `GET /get_data` и подставляет данные в таблицу.

Параллельно физическая кнопка на GPIO 17 (через `key_listener.py` → `usbkey.sh`) делает тот же `POST /make_measurement`.

---
