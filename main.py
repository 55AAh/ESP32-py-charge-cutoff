# noinspection PyUnresolvedReferences
import ensure_deps
import logging
import asyncio
import time

from utils import Utils
from logger import Logger
from wifi import WiFi
from server import Server
from logic import Logic


log = logging.getLogger('MAIN')
log.setLevel(logging.DEBUG)


async def main():
    # Setup utils
    Utils.init_sd_card()

    # Setup logging
    Utils.reset_uptime()
    Logger.setup_file()
    Logger.setup_web()

    # Start server
    server_task = asyncio.create_task(Server.run())

    # Run device logic
    log.info('Executing device logic...')
    logic_task = asyncio.create_task(WiFi.retry_run_task(Logic.execute))
    await logic_task
    log.info('Device logic completed')

    log.info('Waiting for webserver to stop...')
    await server_task


if __name__ == "__main__":
    time.sleep(1)
    print('ENTRY\n')
    try:
        asyncio.run(main())
    except Exception as e:
        Utils.blink_error()
        raise e
    print('\nEXIT')
