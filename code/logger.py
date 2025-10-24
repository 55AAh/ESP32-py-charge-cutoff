import logging
import asyncio
import gc
import os

from utils import Utils


class Logger:
    _root_logger = logging.getLogger()

    @classmethod
    def patch_logging_lib(cls):
        cls._root_logger = logging.getLogger()

        class LogRecord(logging.LogRecord):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            def set(self, *args):
                super().set(*args)
                epoch_time_ms = Utils.get_epoch_time_ms()
                self.ct = epoch_time_ms // 1000
                self.msecs = epoch_time_ms % 1000
                # self.levelname = self.levelname[0]

        logging.LogRecord = LogRecord

        class Formatter(logging.Formatter):
            def __init__(self, *_args, **_kwargs):
                super().__init__(
                    fmt="%(asctime)s.%(msecs)03d - %(levelname)s - %(name)s - %(message)s"
                )

            def usesTime(self):
                return True

            def formatTime(self, _datefmt, record):
                return Utils.format_local_time(record.ct)

        logging.Formatter = Formatter

    @classmethod
    def setup_serial(cls):
        # Setup root logger
        cls._root_logger.setLevel(logging.DEBUG)

        # Create serial handler and set level to debug
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.DEBUG)

        # Add formatter to the handler
        stream_handler.setFormatter(logging.Formatter())

        # Add handler in logger
        cls._root_logger.handlers.clear()
        cls._root_logger.addHandler(stream_handler)

        gc.collect()

    _file_handler = None
    _file_dir_path = "/sd"
    _file_path = _file_dir_path + "/esp32.log"
    _web_streams = {}
    _web_stream_new_id = 0
    _max_stream_buffer_size = 10
    _web_streams_event = asyncio.Event()

    @classmethod
    def setup_file(cls):
        files = sorted([
            f
            for f in os.listdir(cls._file_dir_path)
            if f.startswith("esp32") and f.endswith(".log")
        ])
        last_file_num = 0
        if files:
            try:
                last_file_num = int(files[-1].strip("esp32_").rstrip(".log"))
            except ValueError:
                pass
        cls._file_path = cls._file_dir_path + f"/esp32_{last_file_num + 1:>08}.log"

        # Create file handler and set level to debug
        class FileHandler(logging.FileHandler):
            def emit(self, record):
                super().emit(record)
                self.stream.flush()

        file_handler = FileHandler(cls._file_path, "w")
        file_handler.setLevel(logging.DEBUG)

        # Add formatter to the handler
        file_handler.setFormatter(logging.Formatter())

        # Add handler to logger
        cls._root_logger.addHandler(file_handler)
        cls._file_handler = file_handler

        logging.getLogger("logger").info('Logfile = "%s"', cls._file_path)

        gc.collect()

    @classmethod
    def setup_web(cls):
        _cls = cls

        class WebStreamsHandler(logging.Handler):
            def emit(self, record):
                msg = self.format(record)
                _cls._log_to_web_streams(msg)

        web_handler = WebStreamsHandler()
        web_handler.setLevel(logging.DEBUG)

        # Add formatter to the handler
        web_handler.setFormatter(logging.Formatter())

        # Add handler to logger
        cls._root_logger.addHandler(web_handler)

        gc.collect()

    @classmethod
    def _read_from_file(cls):
        with open(cls._file_path, "r") as f:
            data = f.read().rstrip().split("\n")
            gc.collect()
            return data

    @classmethod
    def register_web_stream(cls) -> int:
        # Create new web stream buffer
        new_id = cls._web_stream_new_id
        cls._web_stream_new_id += 1
        cls._web_streams[new_id] = None
        gc.collect()
        return new_id

    @classmethod
    def _log_to_web_streams(cls, msg: str):
        for stream_id in list(cls._web_streams.keys()):
            stream = cls._web_streams[stream_id]
            if stream is None:
                continue

            stream.append(msg)
            if len(stream) > 10:
                del cls._web_streams[stream_id]

            cls._web_streams_event.set()
        gc.collect()

    @classmethod
    async def fetch_web_stream(cls, stream_id: int):
        gc.collect()
        while True:
            if stream_id not in cls._web_streams:
                return None

            msgs = cls._web_streams[stream_id]
            cls._web_streams[stream_id] = []

            if msgs is None:
                msgs = cls._read_from_file()

            if msgs:
                gc.collect()
                return msgs
            else:
                cls._web_streams_event = asyncio.Event()
                try:
                    await asyncio.wait_for(cls._web_streams_event.wait(), 5)
                except asyncio.TimeoutError:
                    gc.collect()
                    return []


Logger.patch_logging_lib()
Logger.setup_serial()
gc.collect()
