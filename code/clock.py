import machine
import time

from ntp import Ntp


class Clock:
    """This helper class makes use of the external NTP library"""

    renew_time_secs: float = 60
    last_renewed_at: float = 0

    @classmethod
    def setup(cls):
        _rtc = machine.RTC()
        Ntp.set_datetime_callback(_rtc.datetime)
        Ntp.set_hosts((
            "0.pool.ntp.org",
            "1.pool.ntp.org",
            "2.pool.ntp.org",
            "time.google.com",
            "time.aws.com",
            "time.cloudflare.com",
            "pool.ntp.org",
            "time.nist.gov",
        ))
        Ntp.set_ntp_timeout(timeout_s=3)
        cls.get_unix_time_ms()  # Initial sync

    @classmethod
    def get_unix_time_ms(cls) -> int:
        """Returns current UNIX time in milliseconds. Automatically synchronizes RTC via NTP if needed."""
        uptime_s = time.time()

        if (
            cls.last_renewed_at == 0
            or (uptime_s - cls.last_renewed_at) >= cls.renew_time_secs
        ):
            # If the last sync was more than renew_time_secs ago, sync again
            Ntp.rtc_sync()
            cls.last_renewed_at = time.time()
            print("Synced RTC via NTP")

        # Format the time to UNIX epoch
        return Ntp.time_ms(Ntp.EPOCH_1970)
