import serial
import time
import logging
import glob
import requests
from datetime import datetime
import socket

# Настройка логирования
DEBUG_MODE = 1  # 1 - включить подробные вычисления, 0 - выключить
INFO_MODE = 1   # 1 - включить результаты, 0 - выключить
LOG_TO_CONSOLE = 1  # 1 - выводить логи в консоль, 0 - писать в файл
LOG_FILE = '/var/log/measurements.log'
if LOG_TO_CONSOLE == 1:
    handlers = [logging.StreamHandler()]
else:
    handlers = [logging.FileHandler(LOG_FILE)]
log_level = logging.DEBUG if DEBUG_MODE == 1 else logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=handlers
)

def round_to_nearest_5(value):
    """Округляет значение до ближайшего кратного 5."""
    return round(value * 200) / 200  # Умножение на 200 используется для кратности 0,005

def get_local_ip():
    """Определяет локальный IP-адрес устройства."""
    try:
        # Открываем временный UDP-сокет, не отправляя реальные данные
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0)
            s.connect(("8.8.8.8", 80))  # Подключаемся к внешнему хосту
            return s.getsockname()[0]   # Получаем IP-адрес
    except Exception as e:
        logging.error(f"Ошибка при определении IP: {e}")
        return "127.0.0.1"  # Запасной вариант

LOCAL_IP = get_local_ip()
API_URL = f"http://{LOCAL_IP}:5000/update_data"

logging.info(f"Используемый API URL: {API_URL}")

BAUDRATE_LASERS = 19200
TIMEOUT = 1
COMMAND_V = b'\x56'  # Команда запроса версии
COMMAND_D = b'\x44'  # Команда измерения расстояния
STNDR_CONFIG = {
    'baudrate': 19200,
    'bytesize': serial.EIGHTBITS,
    'parity': serial.PARITY_SPACE,
    'stopbits': serial.STOPBITS_ONE,
    'timeout': 1
}
CMD_GET_MASS = b'\x45'

def parse_mass(data):
    """Корректный парсинг значения веса с обработкой знака"""
    if len(data) != 2:
        return None
    raw_value = int.from_bytes(data, byteorder='little')
    sign_bit = (raw_value >> 15) & 0x01
    abs_value = raw_value & 0x7FFF
    return -abs_value if sign_bit else abs_value

def read_response(ser, expected_bytes, timeout=0.5):
    """Надежное чтение ответа с таймаутом"""
    start_time = time.time()
    data = b''
    while time.time() - start_time < timeout:
        data += ser.read(ser.in_waiting)
        if len(data) >= expected_bytes:
            return data[:expected_bytes]
        time.sleep(0.5)
    return data[:expected_bytes]

def send_command_and_get_response(port, baudrate, command, retries=5):
    """Отправляет команду в бинарном формате и получает ответ."""
    for attempt in range(1, retries + 1):
        try:
            with serial.Serial(port, baudrate, timeout=TIMEOUT) as ser:
                logging.debug(f"[{port}] Попытка {attempt}: Отправка команды: {command.hex()}")
                ser.write(command)  # Отправляем бинарную команду
                time.sleep(0.5)  # Ожидание ответа устройства
                response = ser.readline().decode('ascii', errors='ignore').strip()
                logging.debug(f"[{port}] Попытка {attempt}: Получен ответ: {response}")
                # Проверяем корректность ответа
                if command == COMMAND_V and response.startswith("V:") and "," in response:
                    return response
                if command == COMMAND_D and response.startswith("D:") and "," in response:
                    return response
                logging.warning(f"[{port}] Некорректный ответ: {response}")
        except serial.SerialException as e:
            logging.error(f"[{port}] Ошибка порта: {e}")
        except Exception as e:
            logging.error(f"[{port}] Непредвиденная ошибка: {e}")
        time.sleep(attempt)  # Увеличиваем задержку перед повторной попыткой
    logging.error(f"[{port}] Команда {command.hex()} не получила корректного ответа после {retries} попыток.")
    return None

def identify_devices():
    """Идентифицирует устройства и определяет порты лазеров и весов."""
    available_ports = glob.glob("/dev/ttyUSB*")
    logging.info(f"Найденные порты: {available_ports}")
    devices = {}
    calibration_data = {}
    for device in available_ports:
        try:
            # Проверяем, если устройство возвращает пустой ответ, сразу идентифицируем его как весы
            initial_response = send_command_and_get_response(device, BAUDRATE_LASERS, COMMAND_V, retries=1)
            if not initial_response:
                if "scales" not in devices:
                    devices["scales"] = device
                    logging.info(f"Весы найдены на порту: {device}")
                else:
                    logging.warning(f"Дополнительное устройство с пустым ответом найдено на порту: {device}, игнорируется")
                continue
            # Если ответ не пустой, пробуем определить устройство как лазер
            response = initial_response  # Используем уже полученный ответ
            if response:
                laser_id = response.split(",")[0].split(":")[-1][-3:]
                laser_name = f"laser{laser_id}"
                devices[laser_name] = device
                logging.info(f"Лазер {laser_name} найден на порту: {device}")
                # Калибровка лазера
                calibration_response = send_command_and_get_response(device, BAUDRATE_LASERS, COMMAND_D)
                if calibration_response:
                    try:
                        dist, _ = calibration_response.split(',')
                        calibration_data[laser_name] = float(dist.replace("D: ", "").replace("m", "").strip())
                        logging.info(f"Калибровка {laser_name}: {calibration_data[laser_name]} м")
                    except ValueError:
                        logging.error(f"Некорректные данные калибровки для {laser_name}: {calibration_response}")
            else:
                logging.warning(f"Некорректный ответ на порт: {device}. Устройство пропускается.")
        except serial.SerialException as e:
            logging.error(f"Ошибка при работе с портом {device}: {e}")
        except Exception as e:
            logging.error(f"Непредвиденная ошибка: {e}")
    # Проверка на наличие всех устройств
    if "scales" not in devices:
        logging.error("Весы не найдены среди доступных устройств.")
    if not any(k.startswith("laser") for k in devices.keys()):
        logging.warning("Лазеры не найдены среди доступных устройств.")
    logging.info(f"Идентифицированные устройства: {devices}")
    return devices, calibration_data

last_logged_mass = None  # Глобальная переменная для хранения последнего залогированного веса
current_mass_printed = False  # Флаг для отслеживания вывода текущего веса

def log_mass_change(mass, port):
    """Логирует изменения веса только при их наличии."""
    global last_logged_mass, current_mass_printed
    if mass != last_logged_mass:
        logging.debug(f"[{port}] Получены данные веса: {mass} г")
        last_logged_mass = mass
        print(f"Текущий вес: {mass} г")
        current_mass_printed = True
    else:
        if current_mass_printed:
            logging.debug(f"[{port}] Вес не изменился: {mass} г")
            current_mass_printed = False

def read_weight(port):
    """Считывает вес с устройства весов."""
    try:
        with serial.Serial(port, **STNDR_CONFIG) as ser:
            ser.write(CMD_GET_MASS)  # Отправка команды 0x45
            time.sleep(0.5)  # Небольшая задержка
            mass_data = ser.read(2) if ser.in_waiting >= 2 else b''  # Читаем 2 байта
            mass = parse_mass(mass_data)  # Разбираем данные
            logging.debug(f"[{port}] Получены данные веса: {mass_data.hex() if mass_data else 'None'}")
            return mass
    except serial.SerialException as e:
        logging.error(f"[{port}] Ошибка при чтении веса: {e}")
    return None

def main():
    logging.info("Запуск скрипта измерений")
    devices, calibration_data = identify_devices()
    if "scales" not in devices:
        logging.error("Весы не найдены. Завершение работы.")
        return
    last_mass = None
    while True:
        current_mass = read_weight(devices["scales"])
        if current_mass is not None:
            log_mass_change(current_mass, devices["scales"])
            if last_mass is None or current_mass != last_mass:
                data = {
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                }
                if current_mass >= 30:
                    weight_kg = current_mass / 1000.0  # Вес в килограммах
                    weight_kg_str = f"{weight_kg:.3f}"  # Форматирование строки с тремя знаками после запятой
                    data["weight"] = float(weight_kg_str)  # Преобразование обратно в float
                    for laser, port in devices.items():
                        if laser.startswith("laser"):
                            dist_data = send_command_and_get_response(port, BAUDRATE_LASERS, COMMAND_D)
                            if dist_data and dist_data.startswith("D:"):
                                try:
                                    dist_str, accuracy = dist_data.split(',')
                                    dist_value = float(dist_str.replace("D:", "").replace("m", "").strip())
                                    calibrated_distance = calibration_data.get(laser, 0)
                                    item_size_raw = max(0, round(calibrated_distance - dist_value, 3))
                                    item_size_rounded = round_to_nearest_5(item_size_raw)
                                    logging.debug(f"[{laser}] Размер предмета: {item_size_raw}")
                                    logging.info(f"[{laser}] Измеренный размер предмета: {item_size_raw}")
                                    logging.info(f"[{laser}] Округленный размер предмета: {item_size_rounded}")
                                    data[laser] = item_size_rounded
                                except ValueError as e:
                                    logging.error(f"Ошибка обработки данных лазера {laser}: {dist_data}. Причина: {e}")
                            else:
                                logging.error(f"Некорректные данные от лазера {laser}: {dist_data}")
                elif current_mass < -10000:  # -10 кг в граммах
                    data["weight"] = 0.0  # Обнуляем вес
                    for laser in devices:
                        if laser.startswith("laser"):
                            data[laser] = 0.0  # Обнуляем измерения лазеров
                else:
                    data["weight"] = 0.0  # Обнуляем вес
                    for laser in devices:
                        if laser.startswith("laser"):
                            data[laser] = 0.0  # Обнуляем измерения лазеров
                try:
                    response = requests.post(API_URL, json=data, timeout=10)
                    if response.status_code == 200:
                        logging.info("Данные успешно отправлены в API")
                    else:
                        logging.error(f"Ошибка при отправке данных: {response.status_code}")
                except requests.exceptions.RequestException as e:
                    logging.error(f"Ошибка при отправке данных в API: {e}")
                last_mass = current_mass
            else:
                logging.debug(f"Вес не изменился: {current_mass} г")
        time.sleep(1)  # Устанавливаем интервал в 3 секунды

if __name__ == "__main__":
    main()
