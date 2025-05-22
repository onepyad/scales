#!/usr/bin/env python3
import requests
import i2c_lcd2004_driver as lcd_driver
from time import sleep

lcd = lcd_driver.lcd(1)
API_URL = "http://192.168.0.142:5000/get_data"

def safe_str(value):
    return str(value).replace(",", ".")[:6]  # ограничим длину значения

while True:
    try:
        response = requests.get(API_URL, timeout=2)
        data = response.json()

        timestamp  = str(data.get("timestamp", ""))[:20]
        massa      = safe_str(data.get("weight", "?"))
        laser058   = safe_str(data.get("laser058", "?"))
        laser095   = safe_str(data.get("laser095", "?"))
        laser086   = safe_str(data.get("laser086", "?"))

        lcd.lcd_display_string(timestamp, 1, 1)
        lcd.lcd_display_string(f"Massa: {massa}", 2, 1)
        lcd.lcd_display_string(f"058:{laser058} 095:{laser095}", 3, 1)
        lcd.lcd_display_string(f"086:{laser086}", 4, 1)

    except Exception:
        lcd.lcd_display_string("Ошибка API", 1, 1)
        lcd.lcd_display_string("", 2, 1)
        lcd.lcd_display_string("", 3, 1)
        lcd.lcd_display_string("", 4, 1)

    sleep(1)
