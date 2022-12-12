from dataclasses import dataclass
import time


@dataclass()
class Timer:
    initial_time: float
    _offset: float = 0
    _speed: float = 1
    is_paused: bool = False

    @property
    def offset(self):
        return self._offset

    @property
    def speed(self):
        return self._speed

    @offset.setter
    def offset(self, offset: float, /):
        self.change_offset(offset)

    @speed.setter
    def speed(self, speed: float, /):
        self.change_speed(speed)

    def __init__(self, offset: float = 0, speed: float = 1):
        self.initial_time = time.perf_counter()
        self._offset = offset
        self._speed = speed

    def get_elapsed(self) -> float:
        if self.is_paused:
            return self.offset
        return (time.perf_counter() - self.initial_time) * self.speed + self.offset

    def change_offset(self, offset: float, /):
        self.__init__(offset=offset, speed=self.speed)

    def change_speed(self, speed: float, /):
        self.__init__(offset=self.get_elapsed(), speed=speed)

    def reset(self):
        self.offset = 0

    def pause(self):  # use resume after paused for it to work
        self.offset = self.get_elapsed()
        self.is_paused = True

    def resume(self):
        self.is_paused = False
        self.initial_time = time.perf_counter()
