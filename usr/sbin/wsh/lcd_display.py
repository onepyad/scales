#!/usr/bin/env python3
import requests
from RPLCD.i2c import CharLCD
from time import sleep
import socket

# Получение IP-адреса текущего устройства
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"  # fallback

LOCAL_IP = get_local_ip()
API_URL = f"http://{LOCAL_IP}:5000/get_data"

# Настройка дисплея
lcd = CharLCD('PCF8574', address=0x27, port=1, cols=20, rows=4, charmap='A00')

def safe_str(value):
    return str(value).replace(",", ".")[:6]

while True:
    try:
        response = requests.get(API_URL, timeout=2)
        data = response.json()

        timestamp  = str(data.get("timestamp", ""))[:20]
        massa      = safe_str(data.get("weight", "?"))
        laser058   = safe_str(data.get("laser058", "?"))
        laser095   = safe_str(data.get("laser095", "?"))
        laser086   = safe_str(data.get("laser086", "?"))

        lcd.clear()
        lcd.cursor_pos = (0, 0)
        lcd.write_string(timestamp)

        lcd.cursor_pos = (1, 0)
        lcd.write_string(f"Massa: {massa}")

        lcd.cursor_pos = (2, 0)
        lcd.write_string(f"058:{laser058} 095:{laser095}")

        lcd.cursor_pos = (3, 0)
        lcd.write_string(f"086:{laser086}")

    except Exception:
        lcd.clear()
        lcd.cursor_pos = (0, 0)
        lcd.write_string("API error")

    sleep(1)
