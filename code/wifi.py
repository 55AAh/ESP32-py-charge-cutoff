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
    def begin_connecting(cls):
        """Begins connection to WiFi network. Non-blocking."""
        print("Enabling WiFi interface...")
        cls._wlan.active(True)

        print("Initializing WiFi connection...")
        cls._wlan.ifconfig(cls.static_ifconfig)
        cls._wlan.connect(Credentials.network_ssid, Credentials.network_pass)

    @classmethod
    def ensure_connected(cls):
        """Blocks execution until connected."""

        while not cls._wlan.isconnected():
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
                if cls._wlan:
                    cls._wlan.disconnect()
                cls._wlan.active(False)
                # Hopefully, disabling and re-enabling the interface helps
                time.sleep(1)

        # Connection successful
        print(f"ifconfig(): {cls._wlan.ifconfig()}")
        RedLed.turn_on()

    @classmethod
    async def ensure_wifi(cls, task_gen):
        while True:
            try:
                task = task_gen()
                await task
            except OSError as e:
                print(f"WiFi operation error: {e}, disconnecting...")
                if cls._wlan:
                    cls._wlan.disconnect()
                cls._wlan.active(False)
                time.sleep(1)

                cls.begin_connecting()
                cls.ensure_connected()
                time.sleep(1)

                print("Will retry the task now")
            else:
                break
