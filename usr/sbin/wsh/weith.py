import serial
import time
import logging
from logging.handlers import TimedRotatingFileHandler
import glob
import requests
from datetime import datetime
import socket
import os

# Настройка кастомного уровня DATA
DATA_LEVEL = 25
logging.addLevelName(DATA_LEVEL, "DATA")

# Настройка логирования
LOG_LEVEL = 1  # 1=DEBUG, 2=WARNING, 3=INFO, 4=DATA
LEVEL_MAP = {1: logging.DEBUG, 2: logging.WARNING, 3: logging.INFO, 4: DATA_LEVEL}

# Логгеры
logger = logging.getLogger('weith_service')
data_logger = logging.getLogger('weith_service.data')
logger.setLevel(LEVEL_MAP.get(LOG_LEVEL, logging.DEBUG))
data_logger.setLevel(DATA_LEVEL)

# Обработчики
console_handler = logging.StreamHandler()
main_handler = TimedRotatingFileHandler('/var/log/weith_service.log', when='midnight', interval=1, backupCount=7)
data_handler = TimedRotatingFileHandler('/var/log/weith_service_data.log', when='midnight', interval=1, backupCount=7)

# Формат
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s')
for handler in [console_handler, main_handler, data_handler]:
    handler.setFormatter(formatter)

# Фильтр для DATA
class DataFilter(logging.Filter):
    def filter(self, record):
        return record.levelno == DATA_LEVEL

data_handler.addFilter(DataFilter())

# Привязка обработчиков
logger.addHandler(console_handler)
logger.addHandler(main_handler)
data_logger.addHandler(console_handler)
data_logger.addHandler(data_handler)

# Остальной код без изменений до main()
def round_to_nearest_5(value):
    return round(value * 200) / 200

def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0)
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception as e:
        logger.error(f"Ошибка при определении IP: {e}")
        return "127.0.0.1"

LOCAL_IP = get_local_ip()
API_URL = f"http://{LOCAL_IP}:5000/update_data"

BAUDRATE_LASERS = 19200
TIMEOUT = 1
COMMAND_V = b'\x56'
COMMAND_D = b'\x44'
STNDR_CONFIG = {
    'baudrate': 19200,
    'bytesize': serial.EIGHTBITS,
    'parity': serial.PARITY_SPACE,
    'stopbits': serial.STOPBITS_ONE,
    'timeout': 1
}
CMD_GET_MASS = b'\x45'

def parse_mass(data):
    if len(data) != 2:
        return None
    raw_value = int.from_bytes(data, byteorder='little')
    sign_bit = (raw_value >> 15) & 0x01
    abs_value = raw_value & 0x7FFF
    return -abs_value if sign_bit else abs_value

def send_command_and_get_response(port, baudrate, command, retries=5):
    for attempt in range(1, retries + 1):
        try:
            with serial.Serial(port, baudrate, timeout=TIMEOUT) as ser:
                logger.debug(f"[{port}] Попытка {attempt}: Отправка команды: {command.hex()}")
                ser.write(command)
                time.sleep(0.5)
                response = ser.readline().decode('ascii', errors='ignore').strip()
                logger.debug(f"[{port}] Попытка {attempt}: Получен ответ: {response}")
                if command == COMMAND_V and response.startswith("V:") and "," in response:
                    return response
                if command == COMMAND_D and response.startswith("D:") and "," in response:
                    return response
                logger.warning(f"[{port}] Некорректный ответ: {response}")
        except Exception as e:
            logger.error(f"[{port}] Ошибка: {e}")
        time.sleep(attempt)
    return None

def identify_devices():
    available_ports = glob.glob("/dev/ttyUSB*")
    logger.info(f"Найденные порты: {available_ports}")
    devices = {}
    calibration_data = {}
    for device in available_ports:
        try:
            initial_response = send_command_and_get_response(device, BAUDRATE_LASERS, COMMAND_V, retries=1)
            if not initial_response:
                if "scales" not in devices:
                    devices["scales"] = device
                    logger.info(f"Весы найдены на порту: {device}")
                continue
            response = initial_response
            if response:
                laser_id = response.split(",")[0].split(":")[-1][-3:]
                laser_name = f"laser{laser_id}"
                devices[laser_name] = device
                logger.info(f"Лазер {laser_name} найден на порту: {device}")
                calibration_response = send_command_and_get_response(device, BAUDRATE_LASERS, COMMAND_D)
                if calibration_response:
                    try:
                        dist, _ = calibration_response.split(',')
                        calibration_data[laser_name] = float(dist.replace("D:", "").replace("m", "").strip())
                    except ValueError:
                        logger.error(f"Некорректная калибровка {laser_name}: {calibration_response}")
        except Exception as e:
            logger.error(f"Ошибка на порту {device}: {e}")
    return devices, calibration_data

def read_weight(port):
    try:
        with serial.Serial(port, **STNDR_CONFIG) as ser:
            ser.reset_input_buffer()
            ser.write(CMD_GET_MASS)
            start_time = time.time()
            data = b''
            while time.time() - start_time < 1.0:
                if ser.in_waiting >= 2:
                    data = ser.read(2)
                    break
                time.sleep(0.05)
            if not data:
                logger.warning(f"[{port}] Нет данных от весов.")
                return None
            mass = parse_mass(data)
            logger.debug(f"[{port}] Получен вес: {mass} г (сырые данные: {data.hex()})")
            return mass
    except Exception as e:
        logger.error(f"[{port}] Ошибка чтения веса: {e}")
        return None

def main():
    logger.info("Сервис запущен. Ожидание команды от API...")
    devices, calibration_data = identify_devices()
    if "scales" not in devices:
        logger.error("Весы не найдены. Завершение.")
        return

    while True:
        if os.path.exists("/tmp/do_measure.flag"):
            os.remove("/tmp/do_measure.flag")
            logger.info("Получен флаг. Выполняем измерения...")

            current_mass = read_weight(devices["scales"])
            if current_mass is None:
                logger.warning("Не удалось считать вес.")
                continue

            data = {
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "weight": round(current_mass / 1000.0, 3)
            }

            for laser, port in devices.items():
                if laser.startswith("laser"):
                    logger.info(f"Отправка команды измерения на {laser} (порт {port})")
                    dist_data = send_command_and_get_response(port, BAUDRATE_LASERS, COMMAND_D)
                    if dist_data and dist_data.startswith("D:"):
                        try:
                            dist_str, accuracy = dist_data.split(',')
                            dist_value = float(dist_str.replace("D:", "").replace("m", "").strip())
                            calibrated_distance = calibration_data.get(laser, 0)
                            item_size = max(0, round(calibrated_distance - dist_value, 3))
                            data[laser] = round_to_nearest_5(item_size)
                            data_logger.log(DATA_LEVEL, f"{laser}: Измерено {item_size} м, округлено до {data[laser]} м")
                        except Exception as e:
                            logger.error(f"Ошибка лазера {laser}: {e}")
                            data[laser] = 0.0
                    else:
                        logger.warning(f"{laser}: Нет данных от лазера")
                        data[laser] = 0.0

            data_logger.log(DATA_LEVEL, f"Данные для API: {data}")

            try:
                response = requests.post(API_URL, json=data, timeout=10)
                if response.status_code == 200:
                    logger.info("Данные успешно отправлены в API")
                else:
                    logger.error(f"Ошибка API: {response.status_code}")
            except Exception as e:
                logger.error(f"Ошибка отправки в API: {e}")
        else:
            time.sleep(1)

if __name__ == "__main__":
    main()
