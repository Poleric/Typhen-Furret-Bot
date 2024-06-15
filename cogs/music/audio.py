import math
import subprocess
from io import BufferedIOBase
from typing import override

import audioop
from discord import FFmpegPCMAudio
from discord.opus import _OpusStruct as OpusStruct  # noqa

from .errors import Forbidden


class TempoVolumeControlsPCMAudio(FFmpegPCMAudio):
    _MAX_VOL = 2.0
    _volume: float
    _tempo: float

    @override
    def __init__(self, *args, volume: float = 1.0, tempo: float = 1.0, **kwargs):
        self.volume: float = volume
        self.tempo: float = tempo
        self._cache: bytes = b''
        super().__init__(*args, stderr=subprocess.PIPE, **kwargs)  # noqa
        self.check_error()

    @property
    def volume(self) -> float:
        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        self._volume = max(value, 0.0)

    @property
    def tempo(self) -> float:
        return self._tempo

    @tempo.setter
    def tempo(self, value: float) -> None:
        self._tempo = max(value, 0.0)

    @property
    def return_code(self) -> int | None:
        return self._process.poll()

    def check_error(self) -> None:
        if self.return_code == 1:
            if b'403 Forbidden' in self._process.stderr.read():
                raise Forbidden

    def read_frame(self, tempo: float) -> bytes:
        adjusted_size = math.floor(OpusStruct.FRAME_SIZE * tempo)

        ret = self._stdout.read(adjusted_size - len(self._cache))

        return ret

    def adjust_tempo(self, raw_data: bytes, tempo: float, *, sampling_rate: int = OpusStruct.SAMPLING_RATE) -> bytes:
        adjusted_sample_rate = math.ceil(sampling_rate / tempo)
        ret, _ = audioop.ratecv(raw_data, 2, 2, sampling_rate, adjusted_sample_rate, None)
        return ret

    def adjust_volume(self, raw_data: bytes, volume: float) -> bytes:
        return audioop.mul(raw_data, 2, min(volume, self._MAX_VOL))

    def trim_to_frame_size(self, raw_data: bytes, *, frame_size: int = OpusStruct.FRAME_SIZE):
        ret, trim = raw_data[:frame_size], raw_data[frame_size:]
        self._cache = trim
        return ret

    def get_bytes(self, tempo, volume):
        ret = self.read_frame(tempo)
        self.check_error()

        if tempo != 1.0:
            ret = self.adjust_tempo(ret, tempo)
        if volume != 1.0:
            ret = self.adjust_volume(ret, volume)

        self._cache += ret
        return self.trim_to_frame_size(ret)

    @override
    def read(self) -> bytes:
        tempo = self.tempo
        volume = self.volume

        ret = self.get_bytes(tempo, volume)

        # does not work on slow speed...
        if len(ret) < OpusStruct.FRAME_SIZE:
            ret += self.get_bytes(tempo, volume)
            ret = self.trim_to_frame_size(ret)

        if len(ret) != OpusStruct.FRAME_SIZE:
            return b''

        return ret


def create_source(
        source: str | BufferedIOBase,
        *,
        seek_seconds: float = 0,
        tempo: float = 1.0,
        volume: float = 1.0) -> TempoVolumeControlsPCMAudio:
    before_options = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
    if seek_seconds != 0:
        before_options += f" -ss {seek_seconds:.2}"

    options = "-vn -sn"  # skip video, subtitle data

    return TempoVolumeControlsPCMAudio(
        source,
        tempo=tempo,
        volume=volume,
        before_options=before_options,
        options=options

    )
