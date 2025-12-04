"""This module contains classes for controlling the periphery components:
- Onboard small red LED
- Onboard big white LED
- External relay module connected to a GPIO pin"""

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


class Relay:
    """External relay module connected to GPIO 12.
    Is is a Normally Open kind.
    However, we use it to drive a bigger contactor, which is Normally Closed.
    Thus, the logic is reverted. Here, conveniently named methods are provided."""

    _pin = Pin(12, Pin.OUT, Pin.PULL_DOWN)

    @classmethod
    def is_charging_enabled(cls):
        return cls._pin.value() == 0

    @classmethod
    def enable_charging(cls):
        cls._pin.off()

    @classmethod
    def disable_charging(cls):
        cls._pin.on()
