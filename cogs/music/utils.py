from typing import NamedTuple, Self

HOURS_IN_MS = 3600000
MINUTES_IN_MS = 60000
SECONDS_IN_MS = 1000


class tm(NamedTuple):
    hours: int
    minutes: int
    seconds: int
    milliseconds: int

    def __str__(self):
        return self.to_timestamp()

    def to_timestamp(
            self,
            *,
            deliminator: str = ':',
            ms_deliminator: str = '.',
            force_hour: bool = False,
            show_milliseconds: bool = False):
        def to_string():
            if self.hours or force_hour:
                yield f"{self.hours:02}"
            yield f"{self.minutes:02}"
            yield f"{self.seconds:02}"

        if show_milliseconds:
            return deliminator.join(to_string()) + ms_deliminator + f"{self.milliseconds}"
        return deliminator.join(to_string())

    @classmethod
    def from_millis(cls, ms: int) -> Self:
        hours, remainder = divmod(ms, HOURS_IN_MS)
        minutes, remainder = divmod(remainder, MINUTES_IN_MS)
        seconds, milliseconds = divmod(remainder, SECONDS_IN_MS)

        return cls(hours, minutes, seconds, milliseconds)


def md_embed_link(text: str, link: str) -> str:
    """Returns a string to embed a link to text in Markdown."""
    return f"[{text}]({link})"
