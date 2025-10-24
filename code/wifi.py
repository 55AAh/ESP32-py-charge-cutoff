import asyncio
import gc
import network
import logging
import requests

from led import Led
from credentials import Credentials
from utils import Utils

log = logging.getLogger("WiFi")
log.setLevel(logging.DEBUG)


class WiFi:
    _connected = False
    _retries = 0

    @classmethod
    async def connect(cls):
        gc.collect()

        _retries = cls._retries
        cls._retries += 1
        cls._connected = False

        try:
            cls._wlan = network.WLAN(network.STA_IF)

            if _retries >= Utils.max_retries_without_disconnect:
                log.info("Disconnecting WiFi...")
                if cls._wlan.active():
                    cls._wlan.disconnect()
                cls._wlan.active(False)
                cls._retries = 0

            cls._wlan.active(True)

            # Connect to the Wi-Fi network
            log.info("Connecting to WiFi (%s)...", Credentials.network_ssid)
            cls._wlan.connect(Credentials.network_ssid, Credentials.network_pass)

            # Wait until the connection is established
            while not cls._wlan.isconnected():
                with Led.Blink:
                    print(".", end="")
                    await asyncio.sleep(0.1)
                await asyncio.sleep(0.4)
            print(" ok!")

        except OSError as e:
            if cls._wlan:
                cls._wlan.disconnect()
            raise Utils.WiFiError(e)

        # Connection successful
        cls._connected = True
        log.info("Connected, IP Address: %s", cls._wlan.ifconfig()[0])
        gc.collect()

    @classmethod
    async def ensure_connected(cls):
        while not cls._connected:
            try:
                await WiFi.connect()
            except Utils.WiFiError as e:
                log.error(
                    "%s; sleeping for %d s before retrying...",
                    repr(e.args),
                    Utils.wifi_retry_sleep_time,
                )
                await asyncio.sleep(Utils.wifi_retry_sleep_time)

    @classmethod
    async def retry_run_task(cls, task):
        while True:
            await cls.ensure_connected()
            try:
                await task()
                break
            except Utils.WiFiError:
                log.error(
                    "Sleeping for %d s before retrying...", Utils.wifi_retry_sleep_time
                )
                await asyncio.sleep(Utils.wifi_retry_sleep_time)

    @classmethod
    async def request(
        cls,
        method: str,
        url: str,
        headers: dict | None = None,
        json_body: dict | None = None,
    ):
        await asyncio.sleep(0.1)
        gc.collect()
        try:
            with Led.Blink:
                response = requests.request(
                    method.upper(), url, headers=headers, json=json_body, timeout=1
                )
        except OSError as e:
            log.error("%s", repr(e))
            raise Utils.WiFiError(e)
        finally:
            gc.collect()
        return response
