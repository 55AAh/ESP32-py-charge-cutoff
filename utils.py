import asyncio
import gc
from machine import SPI, Pin, reset, soft_reset
from machine import reset_cause, PWRON_RESET, HARD_RESET, WDT_RESET, DEEPSLEEP_RESET, SOFT_RESET
from sdcard import SDCard
import time
import os


class Utils:
    wifi_retry_sleep_time = 30
    max_retries_without_disconnect = 3
    charging_line_delay = 10
    ac_manual_off_delay = 10
    ac_auto_off_delay = 10
    charge_check_max_delay = 60
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
    def get_info(cls):
        mem_free = gc.mem_free()
        mem_total = gc.mem_alloc() + gc.mem_free()
        memory = f'Memory = {mem_total} bytes, {mem_free / mem_total:.0%} free'

        reset_cause_str = 'reset cause = ' + ({
            PWRON_RESET: 'PWRON_RESET',
            HARD_RESET: 'HARD_RESET',
            WDT_RESET: 'WDT_RESET',
            DEEPSLEEP_RESET: 'DEEPSLEEP_RESET',
            SOFT_RESET: 'SOFT_RESET',
        }.get(reset_cause()) or 'UNKNOWN')

        return memory + '; ' + reset_cause_str

    @classmethod
    async def reset_machine(cls, hard=False):
        print(f'Resetting machine (hard={hard}) in 3s...')
        await asyncio.sleep(3)
        if hard:
            reset()
        else:
            soft_reset()

    @classmethod
    def get_epoch_time_ms(cls):
        return time.time_ns() // 1000_000

    @classmethod
    def get_unix_time_ms(cls) -> int:
        return cls.get_epoch_time_ms() + 946684800_000

    @classmethod
    def format_local_time(cls, epoch_time_s):
        local_time = epoch_time_s + 3600 * 2  # Hello DST ;)
        year, month, mday, hour, minute, second, weekday, yearday = time.localtime(local_time)
        time_str = f'{mday:02}.{month:02}.{year % 100:02} {hour:02}:{minute:02}:{second:02}'
        return time_str

    _uptime_base_ms = 0

    @classmethod
    def reset_uptime(cls):
        cls._uptime_base_ms = cls.get_unix_time_ms()

    @classmethod
    def get_uptime_ms(cls) -> int | None:
        return cls.get_unix_time_ms() - cls._uptime_base_ms

    class WiFiError(Exception):
        pass

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
    async def relay_enabled(cls, value: bool | None = None):
        if value is None:
            return cls._relay_pin.value() == 1
        else:
            if value:
                await asyncio.sleep(2)
            cls._relay_pin.value(value)


Utils.setup()
gc.collect()
