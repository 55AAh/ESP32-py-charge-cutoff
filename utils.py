import asyncio
import gc
from machine import SPI, Pin, reset, soft_reset
from sdcard import SDCard
import time
import os


class Utils:
    wifi_retry_sleep_time = 10
    max_retries_without_disconnect = 3
    charging_line_delay = 10
    ac_manual_off_delay = 10
    ac_auto_off_delay = 10
    charge_check_max_delay = 10
    charge_check_add_delay = 10
    full_charge_delay = 10

    @classmethod
    def setup(cls):
        # cls._switch_pin = Pin(16, Pin.IN, Pin.PULL_UP)  # Not available in SPIRAM!
        cls._relay_pin = Pin(12, Pin.OUT, Pin.PULL_DOWN)
        cls.reset_uptime()
        gc.collect()
        gc.enable()
        gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())

    @classmethod
    async def reset_machine(cls, hard=False):
        print(f'Resetting machine (hard={hard}) in 3s...')
        await asyncio.sleep(3)
        if hard:
            reset()
        else:
            soft_reset()

    @classmethod
    def get_unix_time_ms(cls) -> int:
        return time.time_ns() // 1000_000 + 946684800_000

    _uptime_base_ms = 0

    @classmethod
    def reset_uptime(cls):
        cls._uptime_base_ms = cls.get_unix_time_ms()

    @classmethod
    def get_uptime_ms(cls) -> int | None:
        return cls.get_unix_time_ms() - cls._uptime_base_ms

    class WiFiError(Exception):
        pass

    class Blink:
        @classmethod
        def __enter__(cls):
            pin = Pin(33, Pin.OUT)
            pin.off()  # led function is inverted

        @classmethod
        def __exit__(cls, *_args, **_kwargs):
            pin = Pin(33, Pin.OUT)
            pin.on()

    @classmethod
    def blink_error(cls):
        pin = Pin(4, Pin.OUT)
        pin.on()
        time.sleep(0.001)
        pin.off()

    _sd_path = '/sd'

    @classmethod
    def init_sd_card(cls):
        spi = SPI(1, sck=Pin(14), mosi=Pin(15), miso=Pin(2))
        cs = Pin(13)
        sd = SDCard(spi, cs)
        try:
            os.mount(sd, cls._sd_path)
        except OSError as e:
            if e.errno != 1:  # Already mounted
                raise e

    @classmethod
    def is_auto_ac_off_permitted(cls) -> bool:
        # enabled = cls._switch_pin.value() == 1
        enabled = True
        return enabled

    @classmethod
    def disable_charging_line(cls):
        cls._relay_pin.on()


Utils.setup()
gc.collect()
