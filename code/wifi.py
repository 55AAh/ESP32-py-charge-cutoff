import time
import network

from periphery import RedLed, WhiteLed
from credentials import Credentials


class WiFi:
    # This only indicates we should try disabling and re-enabling the interface
    connection_timeout_s = 30

    # We provide predetermined static IP, subnet mask, gateway and DNS server
    # Hopefully, this speeds up connection a little
    static_ifconfig = (
        "192.168.0.92",
        "255.255.255.0",
        "192.168.0.1",
        "192.168.0.1",
    )

    # Network interface
    # STA_IF means we will connect to an existing WiFi network as a client
    _wlan = network.WLAN(network.STA_IF)

    @classmethod
    def begin(cls):
        """Begins WiFi connection process (non-blocking)."""
        print("Initializing WiFi connection...")
        cls._wlan.active(True)
        cls._wlan.ifconfig(cls.static_ifconfig)
        cls._wlan.connect(Credentials.network_ssid, Credentials.network_pass)

    @classmethod
    def connect(cls):
        """Starts connection and blocks execution until connected (unless block=False)."""

        while not cls._wlan.isconnected():
            RedLed.turn_off()
            try:
                started_at = time.time()
                print("Waiting for WiFi connection: ", end="")
                while not cls._wlan.isconnected():
                    print(".", end="")
                    RedLed.turn_on()
                    time.sleep(0.1)
                    RedLed.turn_off()
                    time.sleep(0.1)

                    if time.time() - started_at > cls.connection_timeout_s:
                        print(f" timeout ({cls.connection_timeout_s}s)!")
                        raise OSError("timed out")
                print(" success!")

            except OSError as e:
                print(f"WiFi connection error: {e}!")

                # Hopefully, disabling and re-enabling the interface helps
                try:
                    cls.disable()
                    time.sleep(1)
                    cls.begin()
                except OSError as _e:
                    print(f"WiFi reset error: {_e}!")
                    time.sleep(10)

        # Connection successful
        RedLed.turn_on()

    @classmethod
    def disable(cls):
        """Disables WiFi interface."""

        print("Disabling WiFi interface...")

        if cls._wlan and cls._wlan.active():
            cls._wlan.disconnect()
        cls._wlan.active(False)

        print("WiFi interface disabled")
        RedLed.turn_off()

    @classmethod
    def ensure_wifi_sync(cls, task):
        while True:
            try:
                cls.connect()
                task()

            except OSError as e:
                print(f"WiFi operation error: {e}")

                # Hopefully, disabling and re-enabling the interface helps
                try:
                    cls.disable()
                    time.sleep(10)
                    cls.begin()
                except OSError as _e:
                    print(f"WiFi reset error: {_e}!")
                    time.sleep(10)

            else:
                break

    @classmethod
    async def ensure_wifi(cls, task_gen):
        while True:
            try:
                cls.connect()
                task = task_gen()
                await task

            except OSError as e:
                print(f"WiFi operation error: {e}, disconnecting...")

                # Hopefully, disabling and re-enabling the interface helps
                try:
                    cls.disable()
                    time.sleep(10)
                    cls.begin()
                except OSError as _e:
                    print(f"WiFi reset error: {_e}!")
                    time.sleep(10)

            else:
                break
