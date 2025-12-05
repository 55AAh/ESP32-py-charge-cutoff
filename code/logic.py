import asyncio
from periphery import Relay
from ecoflow import delta2
from logger import getLogger


log = getLogger("LOGIC")


class Logic:
    startup_delay = 10
    device_offline_delay = 60
    start_charging_delay = 10
    ac_manual_off_delay = 10
    ac_auto_off_delay = 10
    charge_check_max_delay = 300
    charge_check_add_delay = 10
    full_charge_delay = 10

    @classmethod
    async def run(cls):
        log(f"Sleeping for {cls.startup_delay}s before executing logic...")
        await asyncio.sleep(cls.startup_delay)

        Relay.enable_charging()
        log("Enabled relay charging")

        await cls.ensure_online()
        await cls.ensure_charging()
        await cls.ensure_ac_off()
        await cls.ensure_battery_full()

        log("Disabling relay charging...")
        Relay.disable_charging()
        log("Relay charging disabled, logic done!")

    @classmethod
    async def ensure_online(cls):
        while True:
            log("Checking Delta2 online status...")
            if await delta2.is_online():
                break
            log(f"Delta2 is offline! Sleeping for {cls.device_offline_delay}s...")
            await asyncio.sleep(cls.device_offline_delay)
        log("Delta2 is online")

    @classmethod
    async def ensure_charging(cls):
        while True:
            log("Requesting charging status...")
            if await delta2.charging_line_plugged():
                break
            log(
                f"Delta2 is not charging! Sleeping for {cls.start_charging_delay}s secs..."
            )
            await asyncio.sleep(cls.start_charging_delay)
        log("Charging line is plugged")

    @classmethod
    async def ensure_ac_off(cls):
        while True:
            log("Requesting AC status...")
            if not await delta2.get_ac_enabled():
                break
            log(f"AC is on. Sleeping for {cls.ac_auto_off_delay}s before disabling...")
            await asyncio.sleep(cls.ac_auto_off_delay)
            log("Disabling AC...")
            await delta2.set_ac_enabled(False)
            # We might lose Wi-Fi here ;)
        log("AC is off")

    @classmethod
    async def ensure_battery_full(cls):
        while True:
            log("Requesting battery status...")
            values = await delta2.battery_status()
            if not values["is_charging"]:
                break

            remaining_time = values["remaining_time_minutes"] * 60
            remaining_chg_time = max(0, remaining_time)
            sleep_time = min(
                remaining_chg_time + cls.charge_check_add_delay,
                cls.charge_check_max_delay,
            )

            log(
                f"Battery is {values['soc']}%, "
                f"{values['remaining_time_minutes']}m until full, "
                f"rechecking in {sleep_time}s...",
            )

            await asyncio.sleep(sleep_time)

        log(
            f"Battery is fully charged, "
            f"waiting for {cls.full_charge_delay}s to settle...",
        )
        await asyncio.sleep(cls.full_charge_delay)
