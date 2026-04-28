#!/usr/bin/env python3

import RPi.GPIO as GPIO
import time
import subprocess
import sys

BUTTON_GPIO = 17
SCRIPT = "/usr/sbin/wsh/usbkey.sh"
COOLDOWN = 3  # секунды между срабатываниями


def log(msg: str) -> None:
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}", flush=True)


GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)

log(f"Ожидание нажатия кнопки на GPIO {BUTTON_GPIO}...")

was_pressed = False
last_trigger_time = 0.0

try:
    while True:
        if GPIO.input(BUTTON_GPIO) == GPIO.LOW:
            now = time.time()
            if not was_pressed and (now - last_trigger_time) >= COOLDOWN:
                log(f"Кнопка нажата → вызов {SCRIPT}")
                subprocess.Popen([SCRIPT])
                last_trigger_time = now
                was_pressed = True
        else:
            was_pressed = False

        time.sleep(0.05)

except KeyboardInterrupt:
    log("Завершение")
    sys.exit(0)
finally:
    GPIO.cleanup()
