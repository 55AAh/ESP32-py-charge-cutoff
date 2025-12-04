# Import logging module
from logger import getLogger, log_error

# And get a logger
log = getLogger("MAIN")

# We don't import anything at the top to escape from possible errors in imported modules


def main():
    """This is the entrypoint of the application.
    `main.py` is automatically executed on boot by Micropython firmware.

    Our job is to wrap the whole application in a try/except block to catch and log all errors.
    """

    print("\n\t__main__\n")

    # Begin connecting to WiFi early to save time
    from wifi import WiFi

    WiFi.begin_connecting()

    # We are ready to run the main application
    import asyncio

    from app import app, catch_error

    log("Starting event loop")
    asyncio.run(catch_error(app()))
    log("Event loop exited. Passing execution to REPL.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log_error(e)
