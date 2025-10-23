from machine import Pin
from time import sleep


class Led:
    class Blink:
        @classmethod
        def __enter__(cls):
            Pin(33, Pin.OUT).off()  # led function is inverted

        @classmethod
        def __exit__(cls, *_args, **_kwargs):
            Pin(33, Pin.OUT).on()

    class BlinkBig:
        @classmethod
        def __enter__(cls):
            Pin(4, Pin.OUT).on()

        @classmethod
        def __exit__(cls, *_args, **_kwargs):
            Pin(4, Pin.OUT).off()

    @classmethod
    def blink_error(cls):
        for _ in range(5):
            with cls.BlinkBig:
                sleep(0.001)
            sleep(0.5)


for _ in range(3):
    with Led.Blink:
        with Led.BlinkBig:
            sleep(0.0001)
    sleep(0.1)
