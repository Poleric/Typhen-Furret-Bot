from typing import Callable


def strip_seconds(seconds: int | float) -> tuple[int, int, int | float]:
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return int(hours), int(minutes), seconds


def timestamp(hours: int, minutes: int, seconds: int | float, *, trim_milliseconds=True) -> str:
    if trim_milliseconds:
        seconds = int(seconds)

    if hours:
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    return f"{minutes:02}:{seconds:02}"


NOT_SUPPORTED_FLAG = "not_supported"


def mark_not_supported[T, **P](func: Callable[P, T]) -> Callable[P, T]:
    setattr(func, NOT_SUPPORTED_FLAG, True)
    return func


def is_func_supported(func: Callable) -> bool:
    return not getattr(func, NOT_SUPPORTED_FLAG, False)
