if __name__ == "__main__":
    print()
    print("bootloader is running")

    import machine
    import time

    pin = machine.Pin(13, machine.Pin.IN, machine.Pin.PULL_UP)
    time.sleep(0.1)

    if pin.value() == 0:
        print("Jumper detected, importing program...")
        import sys

        sys.path.append("code")
        from code.main import main

        print("Program imported, running...")
        main()

    else:
        print("Jumper (GND <-> GPIO13) not connected, skipping program.")
        machine.Pin(33, machine.Pin.OUT).off()  # Turn on small led

    print("bootloader done")
    print()
