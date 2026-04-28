#!/usr/bin/env python3

import RPi.GPIO as GPIO
import time
import subprocess
import os

BUTTON_GPIO = 17
SCRIPT = "/usr/sbin/wsh/usbkey.sh"
LOG_PATH = "/home/scales/logs/key_listener.log"
COOLDOWN = 3  # секунды между срабатываниями

# Убедимся, что каталог для логов существует
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("Ожидание нажатия кнопки...")

was_pressed = False
last_trigger_time = 0

try:
    while True:
        if GPIO.input(BUTTON_GPIO) == GPIO.LOW:
            now = time.time()
            if not was_pressed and (now - last_trigger_time) >= COOLDOWN:
                print("Нажата кнопка — запускаем скрипт")

                # лог в файл
                with open(LOG_PATH, "a") as log:
                    log.write(f"{time.ctime()} — Кнопка нажата → вызов {SCRIPT}\n")

                subprocess.Popen([SCRIPT])
                last_trigger_time = now
                was_pressed = True
        else:
            was_pressed = False

        time.sleep(0.05)

except KeyboardInterrupt:
    print("Завершение")
finally:
    GPIO.cleanup()
