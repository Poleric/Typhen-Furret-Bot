from .abc import *
from .youtube import *
from .soundcloud import *
from .bandcamp import *
from .utils import is_func_supported

SUPPORTED_EXTRACTORS: tuple[type[Extractor], ...] = (
    Youtube,
    Soundcloud,
    Bandcamp
)

SEARCH_SUPPORTED_EXTRACTORS: tuple[type[Extractor], ...] = tuple(
    extractor for extractor in SUPPORTED_EXTRACTORS
    if is_func_supported(extractor.search)
)


def choose_extractor(query: str) -> type[Extractor] | None:
    for extractor in SUPPORTED_EXTRACTORS:
        if extractor.REGEX.match(query):
            return extractor
