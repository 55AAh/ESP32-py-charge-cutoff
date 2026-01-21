"""This file is intended as a simple and failsafe way of logging messages.
It doesn't import other files (apart from credentials.py and urequests from standard library),
and thus is less impacted in case of a bug or error."""

from credentials import Credentials
import urequests


def getLogger(logger_name: str):
    """
    Can be used in a following way:

    ```
    from logger import getLogger

    log = getLogger("MyModule")

    log("This is a log message.")
    ```

    Output: `(MyModule) This is a log message.`
    """

    def namedLogger(text: str):
        _log(f"({logger_name}) {text}")

    return namedLogger


def log_error(e: Exception):
    # Hopefully, this is not a WiFi problem, and we will be able to log the error to Telegram as well

    import io
    import sys

    buf = io.StringIO()
    sys.print_exception(e, buf)  # Traceback and all

    _log(f"An error occurred:\n```\n{buf.getvalue()}\n```")


def _log(text: str):
    """Prints the log message to serial port and tries to send it to Telegram bot."""

    # First, simply print to serial port
    print(text)

    # Then, try to send to Telegram
    body = {
        "chat_id": Credentials.tg_admin_chat_id,
        "text": text,
        "parse_mode": "markdown",
    }

    try:
        response = urequests.get(
            url=f"https://api.telegram.org/bot{Credentials.tg_bot_token}/sendMessage",
            json=body,
        )

        if response.status_code != 200:
            raise ValueError(f"Failed to send log message: {response.text}")

    except Exception as e:
        # If sending fails, just print the error to serial port
        print(f"Error while sending log message to telegram: {e}")
