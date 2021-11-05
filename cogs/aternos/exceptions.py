__all__ = (
    'ServerNotOffline',
    'ServerNotOnline',
    'ServerNotInQueue'
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
