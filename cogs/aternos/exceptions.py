__all__ = (
    'ServerNotOffline',
    'ServerNotOnline',
    'ServerNotInQueue',
    'LogInError',
    'PageError',
    'AccessDenied'
)


class StartError(Exception):
    pass


class ServerNotOffline(StartError):
    pass


class StopError(Exception):
    pass


class ServerNotOnline(StopError):
    pass


class ConfirmError(Exception):
    pass


class ServerNotInQueue(ConfirmError):
    pass


class LogInError(Exception):
    pass


class PageError(Exception):
    pass


class AccessDenied(PageError):
    pass
