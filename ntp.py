import gc
import logging
import ntptime
import asyncio

from led import Led
from utils import Utils

log = logging.getLogger('NTP')
log.setLevel(logging.DEBUG)


class NTP:
    renew_time_secs: float = 60

    @classmethod
    async def sync(cls):
        gc.collect()

        log.info('Starting sync...')
        errors = []
        for host in ['time.google.com', 'time.aws.com', 'time.cloudflare.com', 'pool.ntp.org', 'time.nist.gov']:
            try:
                ntptime.timeout = 3
                ntptime.host = host
                with Led.Blink:
                    ntptime.settime()

            except OSError as e:
                errors.append(e)
                log.error('Failed with "%s": %s', host, repr(e))
                await asyncio.sleep(1)

            else:
                Utils.reset_uptime()
                log.info('Sync successful, current UNIX timestamp is %d', Utils.get_unix_time_ms() // 1000)
                cls._last_sync_time_ms = Utils.get_unix_time_ms()
                gc.collect()
                return

        log.error('Sync failed!')
        raise Utils.WiFiError(errors)

    _last_sync_time_ms = 0

    @classmethod
    async def ensure_synced(cls):
        if Utils.get_unix_time_ms() - cls._last_sync_time_ms > cls.renew_time_secs * 1000:
            await cls.sync()
