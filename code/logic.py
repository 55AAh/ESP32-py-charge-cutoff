import asyncio
import logging

from led import Led
from credentials import Credentials
from delta2 import Delta2
from ecoflow_api import EcoflowDeviceApi
from utils import Utils


class Logic:
    device_api = EcoflowDeviceApi(
        Credentials.access_key, Credentials.secret_key, Credentials.sn
    )
    delta2 = Delta2(device_api)

    @classmethod
    async def execute(cls):
        await cls.prepare()
        await cls.ensure_charging_line_plugged()
        await cls.ensure_ac_off()
        await cls.ensure_battery_charged()
        await cls.disable_charging_line()

    @classmethod
    async def prepare(cls):
        log = logging.getLogger("LOGIC0")
        log.setLevel(logging.DEBUG)
        log.info("Sleeping for %d s before executing logic...", Utils.startup_delay)
        await asyncio.sleep(Utils.startup_delay)
        log.info("Enabling charging line via relay...")
        await Utils.relay_enabled(False)
        log.info("Charging line enabled")
        log.info("Checking device online status...")
        while not await cls.delta2.is_online():
            log.warning(
                "Device is offline! Sleeping for %d secs...",
                Utils.device_offline_delay,
            )
            with Led.Blink:
                await asyncio.sleep(Utils.device_offline_delay)
        log.info("Device is online")

    @classmethod
    async def ensure_charging_line_plugged(cls):
        log = logging.getLogger("LOGIC1")
        log.setLevel(logging.DEBUG)
        log.info("Requesting charging line state...")
        while not await cls.delta2.charging_line_plugged():
            log.warning(
                "Charging line is not plugged! Sleeping for %d secs...",
                Utils.charging_line_delay,
            )
            with Led.Blink:
                await asyncio.sleep(Utils.charging_line_delay)
        log.info("Charging line is plugged")

    @classmethod
    async def ensure_ac_off(cls):
        log = logging.getLogger("LOGIC2")
        log.setLevel(logging.DEBUG)
        log.info("Requesting AC state...")
        while await cls.delta2.get_ac_enabled():
            log.info("AC is on")
            if Utils.is_auto_ac_off_permitted():
                log.info(
                    "Sleeping for %d s before disabling...", Utils.ac_auto_off_delay
                )
                with Led.Blink:
                    await asyncio.sleep(Utils.ac_auto_off_delay)
                log.info("Disabling AC...")
                await cls.delta2.set_ac_enabled(False)
                with Led.Blink:
                    await asyncio.sleep(5)
                # We might lose Wi-Fi here ;)
            else:
                log.info(
                    "Auto AC disabling is not permitted, sleeping for %d s before rechecking...",
                    Utils.ac_manual_off_delay,
                )
                with Led.Blink:
                    await asyncio.sleep(Utils.ac_manual_off_delay)
        log.info("AC is off")

    @classmethod
    async def ensure_battery_charged(cls):
        log = logging.getLogger("LOGIC3")
        log.setLevel(logging.DEBUG)
        log.info("Requesting battery state...")
        while await cls.delta2.is_charging():
            log.info("Battery is charging, estimating remaining time...")
            remain_time = await cls.delta2.remain_time_minutes() * 60
            remain_chg_time = max(0, remain_time)
            sleep_time = min(
                remain_chg_time + Utils.charge_check_add_delay,
                Utils.charge_check_max_delay,
            )
            log.info(
                "Reported %d s until full charge, sleeping for %d s...",
                remain_time,
                sleep_time,
            )
            with Led.Blink:
                await asyncio.sleep(sleep_time)

        log.info(
            f"Battery is fully charged, waiting for %d s to settle...",
            Utils.full_charge_delay,
        )
        with Led.Blink:
            await asyncio.sleep(Utils.full_charge_delay)

    @classmethod
    async def disable_charging_line(cls):
        log = logging.getLogger("LOGIC4")
        log.setLevel(logging.DEBUG)
        log.info("Disabling charging line via relay...")
        await Utils.relay_enabled(True)
        log.info("Charging line disabled")
