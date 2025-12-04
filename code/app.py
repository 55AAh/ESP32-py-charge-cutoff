# External NTP library to sync RTC (correct time is required by Ecoflow Api)
# https://github.com/ekondayan/micropython-ntp/blob/main/src/ntp.py
import ntp

# External library that implements HMAC-SHA1 algorithm
# https://github.com/micropython/micropython-lib/blob/master/python-stdlib/hmac/hmac.py
import hmac

# External library that implements FTP server
# https://github.com/robert-hh/FTP-Server-for-ESP8266-ESP32-and-PYBD/blob/master/uftpd.py
# Starts automatically on import.
# It binds a socket listener on 0.0.0.0:21, so WiFi failures don't affect it.
import uftpd

# External library that implements asynchronous requests client for MicroPython
import aiohttp


import asyncio

from logger import log_error
from periphery import RedLed
from wifi import WiFi
from clock import Clock
from bot import TelegramBot
from logic import Logic


async def app():
    # Lets's turn on an LED to indicate that we are alive
    RedLed.turn_on()

    import gc

    # Enable automatic garbage collection
    gc.enable()

    # Wait until WiFi is connected
    WiFi.ensure_connected()

    # Setup clock and synchronize RTC via NTP
    Clock.setup()

    # Start Telegram bot
    bot_task = asyncio.create_task(catch_error(WiFi.ensure_wifi(TelegramBot.listen)))

    # Start cutoff logic
    cutoff_task = asyncio.create_task(catch_error(WiFi.ensure_wifi(Logic.run)))

    # Await tasks
    await bot_task
    await cutoff_task


async def catch_error(awaitable):
    try:
        await awaitable
    except Exception as e:
        log_error(e)
