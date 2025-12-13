"""This module contains classes for controlling the periphery components:
- Onboard small red LED
- Onboard big white LED
"""

from machine import Pin


class RedLed:
    """Onboard small red LED controlled by GPIO 33 (inverted logic)."""

    _pin = Pin(33, Pin.OUT, Pin.PULL_UP)

    @classmethod
    def turn_on(cls):
        cls._pin.off()  # function is inverted

    @classmethod
    def turn_off(cls):
        cls._pin.on()  # function is inverted


class WhiteLed:
    """Onboard big white LED controlled by GPIO 4."""

    _pin = Pin(4, Pin.OUT, Pin.PULL_DOWN)

    @classmethod
    def turn_on(cls):
        cls._pin.on()

    @classmethod
    def turn_off(cls):
        cls._pin.off()
