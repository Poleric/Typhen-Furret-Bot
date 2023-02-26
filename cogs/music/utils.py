from typing import Callable, Type
import logging


def max_retry(func: Callable, max_retries, exceptions: Type[Exception] | tuple[Type[Exception], ...] = None):
    retries = 0
    while True:
        try:
            return func()
        except exceptions as e:
            if retries > max_retries:
                raise e from None
            logging.exception(f"Exception catched, retrying. On retries {retries}")
            retries += 1

