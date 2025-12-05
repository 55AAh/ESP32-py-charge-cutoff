import asyncio
import machine

import aiohttp

from credentials import Credentials
from periphery import Relay
from ecoflow import delta2
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
        log("Listening for updates!")

        while True:
            updates = await cls.get_updates()

            for update in updates:
                cls._offset = update["update_id"] + 1

                await cls.handle_update(update)
                if cls.should_stop:
                    return

            await asyncio.sleep(1)

    @classmethod
    async def send_text(cls, text, reply_markup=None):
        body = {
            "chat_id": Credentials.tg_chat_id,
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
    async def edit_message(cls, message_id: int, new_text: str):
        body = {
            "chat_id": Credentials.tg_chat_id,
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
        if str(chat_id) != str(Credentials.tg_chat_id):
            log(f"Ignored message from chat_id = '{chat_id}'")
            return

        text = message.get("text", "")
        if text == "/start":
            log(f"Received {text} command")
            await cls.send_text(
                "Sending you the keyboard.",
                reply_markup={
                    "keyboard": [
                        [{"text": "Status"}],
                        [{"text": "Toggle AC"}],
                        [{"text": "Toggle relay"}],
                        [{"text": "Reset soft"}],
                        [{"text": "Reset hard"}],
                        [{"text": "Stop bot"}],
                    ],
                    "one_time_keyboard": True,
                },
            )

        elif text == "Status":
            log(f"Received {text} command")

            is_charging_enabled = Relay.is_charging_enabled()
            log(
                f"Relay charging is {'enabled ✅️' if is_charging_enabled else 'disabled ❌'}"
            )

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

        elif text == "Toggle relay":
            log(f"Received {text} command")
            is_charging_enabled = Relay.is_charging_enabled()
            if is_charging_enabled:
                Relay.disable_charging()
                log("Disabled relay charging ❌")
            else:
                Relay.enable_charging()
                log("Enabled relay charging ✅️")

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
