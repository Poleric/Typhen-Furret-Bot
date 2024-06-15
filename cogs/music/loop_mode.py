from enum import Enum, auto

__all__ = (
    "LoopMode"
)


class LoopMode(Enum):
    NO_LOOP = auto()
    LOOP_SONG = auto()
    LOOP_QUEUE = auto()
