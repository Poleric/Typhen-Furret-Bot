import os
import discord
import logging
from logging import StreamHandler
from logging.handlers import TimedRotatingFileHandler


def setup_logging(*, log_directory: str = "./logs") -> None:
    # info logger to stdout
    stream_handler = StreamHandler()
    stream_handler.setLevel(level=logging.INFO)
    discord.utils.setup_logging(handler=stream_handler, root=True)

    # debug logger to file
    os.makedirs(log_directory, exist_ok=True)
    file_handler = TimedRotatingFileHandler(
        filename=f"{log_directory}/bot.log",
        when="midnight",
        backupCount=7,
        encoding="utf-8"
    )
    formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', "%Y-%m-%d %H:%M:%S", style='{')
    discord.utils.setup_logging(handler=file_handler, formatter=formatter, level=logging.DEBUG, root=True)
