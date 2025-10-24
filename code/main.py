# noinspection PyUnresolvedReferences
import logging
import asyncio
import time

from led import Led
from utils import Utils
from logger import Logger
from wifi import WiFi
from server import Server
from logic import Logic


log = logging.getLogger("MAIN")
log.setLevel(logging.DEBUG)


async def run():
    with Led.BlinkBig:
        time.sleep(0.0001)

    # Setup utils
    Utils.init_sd_card()

    # Setup logging
    Utils.reset_uptime()
    Logger.setup_file()
    Logger.setup_web()

    log.info(Utils.get_info())

    # Start server
    server_task = asyncio.create_task(Server.run())

    # Run device logic
    log.info("Executing device logic...")
    logic_task = asyncio.create_task(WiFi.retry_run_task(Logic.execute))
    await logic_task
    log.info("Device logic completed")

    log.info("Webserver continues running...")
    await server_task


def main():
    try:
        asyncio.run(run())
    except Exception as e:
        Led.blink_error()
        raise e


if __name__ == "__main__":
    main()
