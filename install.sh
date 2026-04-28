#!/bin/bash
# install.sh: автоматическая установка проекта scales на Raspberry Pi.
# Запускать от root: sudo ./install.sh
#
# Поведение можно настроить через переменные окружения:
#   SCALES_USER       — системный пользователь        (default: scales)
#   SCALES_HOME       — домашний каталог пользователя (default: /home/$SCALES_USER)
#   SCALES_VENV       — путь к venv                   (default: $SCALES_HOME/venv)
#   SCALES_BIN        — куда копируются скрипты       (default: /usr/sbin/wsh)
#   SCALES_SYSTEMD    — каталог systemd-юнитов        (default: /etc/systemd/system)
#
# Логи всех сервисов пишутся в системный journal — смотреть через
# `journalctl -u <unit> -f`.

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "Запустите скрипт от root (sudo)" >&2
    exit 1
fi

# --- Параметры установки -----------------------------------------------------

SCALES_USER="${SCALES_USER:-scales}"
SCALES_HOME="${SCALES_HOME:-/home/${SCALES_USER}}"
SCALES_VENV="${SCALES_VENV:-${SCALES_HOME}/venv}"
SCALES_BIN="${SCALES_BIN:-/usr/sbin/wsh}"
SCALES_SYSTEMD="${SCALES_SYSTEMD:-/etc/systemd/system}"

# Каталог исходников (там, где лежит этот install.sh)
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SERVICES=(api_service weith_service lcd_display key_service)

echo "==> Установка scales"
echo "    user        = ${SCALES_USER}"
echo "    home        = ${SCALES_HOME}"
echo "    venv        = ${SCALES_VENV}"
echo "    scripts dir = ${SCALES_BIN}"
echo "    systemd dir = ${SCALES_SYSTEMD}"
echo "    src dir     = ${SRC_DIR}"
echo

# --- 1. Системные пакеты ----------------------------------------------------

echo "==> [1/6] Системные пакеты"
apt update
apt install -y python3 python3-venv python3-pip python3-smbus i2c-tools curl

# Включить I2C (нужно для LCD). Не падать, если raspi-config недоступен.
if command -v raspi-config >/dev/null 2>&1; then
    raspi-config nonint do_i2c 0 || true
fi

# --- 2. Пользователь --------------------------------------------------------

echo "==> [2/6] Пользователь ${SCALES_USER}"
if ! id "${SCALES_USER}" >/dev/null 2>&1; then
    useradd -m -s /bin/bash "${SCALES_USER}"
    echo "    создан пользователь ${SCALES_USER} (пароль не задан, при необходимости: passwd ${SCALES_USER})"
else
    echo "    уже существует"
fi

# Доступ к GPIO/I2C/UART
for grp in gpio i2c dialout; do
    if getent group "${grp}" >/dev/null 2>&1; then
        usermod -aG "${grp}" "${SCALES_USER}" || true
    fi
done

# --- 3. Каталоги ------------------------------------------------------------

echo "==> [3/6] Каталоги"
mkdir -p "${SCALES_BIN}"

# --- 4. Скрипты -------------------------------------------------------------

echo "==> [4/6] Скрипты → ${SCALES_BIN}"
install -m 0755 -o "${SCALES_USER}" -g "${SCALES_USER}" \
    "${SRC_DIR}/usr/sbin/wsh/api.py"          "${SCALES_BIN}/api.py"
install -m 0755 -o "${SCALES_USER}" -g "${SCALES_USER}" \
    "${SRC_DIR}/usr/sbin/wsh/weith.py"        "${SCALES_BIN}/weith.py"
install -m 0755 -o "${SCALES_USER}" -g "${SCALES_USER}" \
    "${SRC_DIR}/usr/sbin/wsh/lcd_display.py"  "${SCALES_BIN}/lcd_display.py"
install -m 0755 -o "${SCALES_USER}" -g "${SCALES_USER}" \
    "${SRC_DIR}/usr/sbin/wsh/key_listener.py" "${SCALES_BIN}/key_listener.py"
install -m 0755 -o "${SCALES_USER}" -g "${SCALES_USER}" \
    "${SRC_DIR}/usr/sbin/wsh/usbkey.sh"       "${SCALES_BIN}/usbkey.sh"

# --- 5. Виртуальное окружение и зависимости --------------------------------

echo "==> [5/6] venv → ${SCALES_VENV}"
if [ ! -x "${SCALES_VENV}/bin/python" ]; then
    sudo -u "${SCALES_USER}" python3 -m venv "${SCALES_VENV}"
fi
sudo -u "${SCALES_USER}" "${SCALES_VENV}/bin/pip" install --upgrade pip
sudo -u "${SCALES_USER}" "${SCALES_VENV}/bin/pip" install -r "${SRC_DIR}/requirements.txt"

# --- 6. systemd-юниты -------------------------------------------------------

echo "==> [6/6] systemd-юниты"
for svc in "${SERVICES[@]}"; do
    src_unit="${SRC_DIR}/etc/systemd/system/${svc}.service"
    dst_unit="${SCALES_SYSTEMD}/${svc}.service"
    if [ ! -f "${src_unit}" ]; then
        echo "    пропуск: ${src_unit} не найден" >&2
        continue
    fi
    install -m 0644 -o root -g root "${src_unit}" "${dst_unit}"
done

# Если venv нестандартный — заменить путь к python в скопированных юнитах.
if [ "${SCALES_VENV}" != "/home/scales/venv" ] || [ "${SCALES_BIN}" != "/usr/sbin/wsh" ]; then
    for svc in "${SERVICES[@]}"; do
        dst_unit="${SCALES_SYSTEMD}/${svc}.service"
        [ -f "${dst_unit}" ] || continue
        sed -i \
            -e "s|/home/scales/venv|${SCALES_VENV}|g" \
            -e "s|/usr/sbin/wsh|${SCALES_BIN}|g" \
            "${dst_unit}"
    done
fi

systemctl daemon-reload
for svc in "${SERVICES[@]}"; do
    systemctl enable "${svc}.service"
    systemctl restart "${svc}.service"
done

echo
echo "==> Готово."
echo "    Логи: journalctl -u <api_service|weith_service|lcd_display|key_service> -f"
echo "    Если включали I2C впервые — может потребоваться перезагрузка."
echo "    Проверка: curl http://127.0.0.1:5000/get_data"
