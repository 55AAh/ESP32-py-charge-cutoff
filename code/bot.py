import asyncio
import time
import machine

import aiohttp

from credentials import Credentials
from ecoflow import delta2
from tuya import tuya_switch
from logger import getLogger

log = getLogger("BOT")


class TelegramBot:
    long_polling_timeout_s = 60  # long polling timeout

    should_stop = False

    _session = aiohttp.ClientSession(
        f"https://api.telegram.org/bot{Credentials.tg_bot_token}"
    )
    _offset = 0

    @classmethod
    async def get_updates(cls):
        async with cls._session.get(
            "/getUpdates",
            json={
                "offset": cls._offset,
                "limit": 10,
                "timeout": cls.long_polling_timeout_s,
                "allowed_updates": ["message"],
            },
        ) as response:
            jo = await response.json()
            updates = jo.get("result", [])
            return updates

    @classmethod
    async def listen(cls):
        log("POWERON")

        while True:
            updates = await cls.get_updates()

            for update in updates:
                cls._offset = update["update_id"] + 1

                await cls.handle_update(update)
                if cls.should_stop:
                    return

            await asyncio.sleep(1)

    @classmethod
    async def send_info(cls):
        def format_time(seconds):
            # Get the current time as an 8-tuple:
            # (year, month, mday, hour, minute, second, weekday, yearday)
            now = time.gmtime(seconds + 3600 * 2)  # UTC+2

            # Format as "DD.MM.YYYY HH:MM"
            time_string = "{:02d}.{:02d}.{:04d} {:02d}:{:02d}".format(
                now[2], now[1], now[0], now[3], now[4]
            )
            return time_string

        def format_interval(seconds):
            days = seconds // (3600 * 24)
            hours = (seconds % (3600 * 24)) // 3600
            minutes = (seconds % 3600) // 60
            if days > 0:
                return f"{days} дн. {hours} год. {minutes} хв."
            elif hours > 0:
                return f"{hours} год. {minutes} хв."
            else:
                return f"{minutes} хв."

        def format_info(
            start_time: float, start_soc: int, now_time: float, now_soc: int
        ):
            info = f"Дали світло:\n{format_time(start_time)} (заряд {start_soc}%)"
            info += f"\nБуло до:\n{format_time(now_time)} (заряд {now_soc}%)"
            info += f"\n({format_interval(now_time - start_time)})"
            return info

        start_soc = await delta2.soc()
        start_time = time.time()

        current_info = format_info(start_time, start_soc, start_time, start_soc)
        info_message = await cls.send_text(Credentials.tg_info_chat_id, current_info)
        info_message_id = info_message["message_id"]

        while True:
            await asyncio.sleep(60)  # every minute

            now_soc = await delta2.soc()
            now_time = time.time()
            new_info = format_info(start_time, start_soc, now_time, now_soc)

            if new_info != current_info:
                await cls.edit_message(
                    Credentials.tg_info_chat_id, info_message_id, new_info
                )
                current_info = new_info

    @classmethod
    async def send_text(cls, chat_id, text, reply_markup=None):
        body = {
            "chat_id": chat_id,
            "text": text,
        }

        if reply_markup:
            body["reply_markup"] = reply_markup

        async with cls._session.get(
            "/sendMessage",
            json=body,
        ) as response:
            if response.status != 200:
                raise ValueError(f"Failed to send message: {await response.text()}")
            jo = await response.json()
            return jo.get("result")

    @classmethod
    async def edit_message(cls, chat_id, message_id: int, new_text: str):
        body = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": new_text,
        }

        async with cls._session.get(
            "/editMessageText",
            json=body,
        ) as response:
            if response.status != 200:
                raise ValueError(f"Failed to edit message: {await response.text()}")

    @classmethod
    async def handle_update(cls, update):
        message = update.get("message", {})
        chat_id = message.get("chat", {}).get("id")

        if str(chat_id) != str(Credentials.tg_admin_chat_id):
            if str(chat_id) == str(Credentials.tg_info_chat_id):
                return  # Ignore messages from info chat

            log(f"Ignored message from chat_id = '{chat_id}'")
            return

        text = message.get("text", "")
        if text == "/start":
            log(f"Received {text} command")
            await cls.send_text(
                Credentials.tg_admin_chat_id,
                "Sending you the keyboard.",
                reply_markup={
                    "keyboard": [
                        [{"text": "Status"}],
                        [{"text": "Toggle AC"}],
                        [{"text": "Relay OFF"}],
                        [{"text": "Reset soft"}],
                        [{"text": "Reset hard"}],
                        [{"text": "Stop bot"}],
                    ],
                    "one_time_keyboard": True,
                },
            )

        elif text == "Status":
            log(f"Received {text} command")

            is_online = await delta2.is_online()
            log(f"Device is {'online ✅️' if is_online else 'offline ❌'}")

            params = await delta2._api.get_params([
                "mppt.cfgAcEnabled",
                "bms_emsStatus.chgLinePlug",
                "bms_bmsStatus.chgState",
                "pd.remainTime",
                "bms_bmsStatus.soc",
            ])
            text = (
                f"Device status:\n"
                f"AC: {'✅️' if params['mppt.cfgAcEnabled'] == 1 else '❌'}\n"
                f"Charging line: {'✅️' if params['bms_emsStatus.chgLinePlug'] == 1 else '❌'}\n"
                f"Charging: {'✅️' if params['bms_bmsStatus.chgState'] != 0 else '❌'}\n"
                f"Remaining time: {params['pd.remainTime']} minutes\n"
                f"SOC: {params['bms_bmsStatus.soc']}%"
            )
            log(text)

        elif text == "Relay OFF":
            log(f"Received {text} command")
            log("Turning the relay off... Goodbye!)")
            await tuya_switch.set_switch(False)

        elif text == "Toggle AC":
            log(f"Received {text} command")
            is_ac_enabled = await delta2.get_ac_enabled()
            if is_ac_enabled:
                await delta2.set_ac_enabled(False)
                log("Disabled AC ❌")
            else:
                await delta2.set_ac_enabled(True)
                log("Enabled AC ✅️")

        elif text == "Reset soft" or text == "Reset hard" or text == "Stop bot":
            log(f"Received {text} command")
            offset = update["update_id"] + 1
            async with cls._session.get(
                "/getUpdates",  # clear up current message
                json={
                    "offset": offset,
                    "limit": 1,
                    "allowed_updates": ["message"],
                },
            ):
                pass

            if text == "Reset soft":
                log("Soft resetting machine...")
                machine.soft_reset()

            elif text == "Reset hard":
                log("Hard resetting machine...")
                machine.reset()

            elif text == "Stop bot":
                log(f"Received {text} command")
                cls.should_stop = True
