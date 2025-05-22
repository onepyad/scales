# 🌟 Развертывание на Raspberry Pi 3

Пошаговое руководство для установки и запуска проекта на Raspberry Pi 3.

## Зависимости
- Python 3 и пакетный менеджер `pip`
- Библиотеки из `requirements.txt`:
  - flask
  - requests
  - pyserial

---

## 📥 0. Скачивание файлов с GitHub

1. **Клонирование репозитория**  
   Скачайте файлы проекта из репозитория GitHub:  
   ```bash
   git clone https://github.com/onepyad/scales.git
   cd scales
   ```

2. **Проверка содержимого**  
   Убедитесь, что файлы, такие как `requirements.txt` и директории `usr/sbin/wsh` и `etc/systemd/system`, присутствуют:  
   ```bash
   ls -l
   ```

> **Примечание**: Если `git` не установлен, установите его с помощью `sudo apt install git -y`.

---

## 🛠 1. Подготовка системы

1. **Обновление пакетов**  
   Обновите систему:  
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **Создание пользователя**  
   Создайте пользователя `scales` с паролем `!QAZxsw2`:  
   ```bash
   sudo adduser scales
   sudo usermod -aG sudo scales  # Добавить в sudo (опционально)
   ```

---

## 🐍 2. Установка Python

1. **Установка инструментов**  
   Установите Python 3 и зависимости:  
   ```bash
   sudo apt install python3 python3-venv python3-pip -y
   ```

2. **Виртуальное окружение**  
   Настройте и активируйте окружение в директории проекта:  
   ```bash
   cd ~/scales
   python3 -m venv /home/scales/venv
   source /home/scales/venv/bin/activate
   pip install -r requirements.txt
   ```

---

## 📂 3. Размещение скриптов и логов

1. **Копирование скриптов**  
   Перейдите в директорию проекта и скопируйте скрипты в `/usr/sbin/wsh`:  
   ```bash
   cd ~/scales
   sudo mkdir -p /usr/sbin/wsh
   sudo cp usr/sbin/wsh/*.py /usr/sbin/wsh/
   sudo chown -R scales:scales /usr/sbin/wsh
   sudo chmod 755 /usr/sbin/wsh/*.py
   ```

2. **Директория для логов**  
   Создайте директорию для логов:  
   ```bash
   sudo mkdir -p /home/scales/logs
   sudo chown -R scales:scales /home/scales/logs
   ```

---

## ⚙️ 4. Настройка systemd

1. **Копирование юнитов**  
   Перейдите в директорию проекта и скопируйте файлы сервисов:  
   ```bash
   cd ~/scales
   sudo cp etc/systemd/system/api_service.service /etc/systemd/system/
   sudo cp etc/systemd/system/weith_service.service /etc/systemd/system/
   ```

2. **Запуск сервисов**  
   Активируйте и запустите сервисы:  
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable api_service.service
   sudo systemctl enable weith_service.service
   sudo systemctl start api_service.service
   sudo systemctl start weith_service.service
   ```

---

## 🔍 5. Управление сервисами

- **Просмотр логов**  
   ```bash
   sudo journalctl -u api_service.service -f
   sudo journalctl -u weith_service.service -f
   ```

- **Управление сервисами**  
   ```bash
   sudo systemctl stop api_service.service
   sudo systemctl restart api_service.service
   sudo systemctl status api_service.service

   sudo systemctl stop weith_service.service
   sudo systemctl restart weith_service.service
   sudo systemctl status weith_service.service
   ```

---

## 🌐 6. API через `curl`

API доступен на порту **5000**:  
```bash
# Получить данные
curl http://<PI_IP>:5000/get_data

# Новое измерение
curl -X POST http://<PI_IP>:5000/make_measurement

# Перезапуск сервиса
curl -X POST http://<PI_IP>:5000/restart_service
```

> Замените `<PI_IP>` на IP-адрес Raspberry Pi.

---

## 🖥 7. API через PowerShell

Используйте порт **5000** для запросов:  
```powershell
# Получить данные
Invoke-RestMethod -Uri "http://<PI_IP>:5000/get_data"

# Новое измерение
Invoke-RestMethod -Method Post -Uri "http://<PI_IP>:5000/make_measurement"

# Перезапуск сервиса
Invoke-RestMethod -Method Post -Uri "http://<PI_IP>:5000/restart_service"
```

> Замените `<PI_IP>` на IP-адрес Raspberry Pi.

---

## 📜 8. Логирование

Скрипт `weith.py` сохраняет логи в `/home/scales/logs`:  
- `weith_service.log` — логи сервиса.  
- `weith_service_data.log` — данные измерений.

---

## 💡 9. Логика работы с 1С

В интерфейсе 1С есть кнопка Сделать измерение:  
- 1С обращается к API сервесу и шлет запрос `make_measurement`,  
- `API` отправляет команду скрипту `/usr/sbin/wsh/weith.py` на измерение,
- Скрипт измеряет и передает измеренные данные обратно в API
- 1C через несколько секунд делает запрос к API `get_data` для получения и подстановки данных в таблицу.

---
