__all__ = (
    'Online',
    'Offline',
    'Crashed',
    'Loading',
    'Preparing',
    'Starting',
    'Restarting',
    'Stopping',
    'Saving',
    'WaitingInQueue'
)


# Server load process
# Offline -> Preparing -> Loading -> Starting -> Online -> Stopping -> Saving -> Offline
class BaseStatus:
    def repr(self):
        return str(self)


# Online type statuses
class Online(BaseStatus):
    """
    actions
    - stop
    - restart
    """
    COLOR = 0x1fd78d

    def __str__(self):
        return 'Online'

    def __bool__(self):
        return True


# Offline type statuses
class Offline(BaseStatus):
    """
    actions
    - start
    """
    COLOR = 0xf62451

    def __str__(self):
        return 'Offline'

    def __bool__(self):
        return False


class Crashed(Offline):
    """
    actions
    - start
    """
    def __str__(self):
        return 'Crashed'


# Loading type statuses
class Loading(BaseStatus):
    """
    Aternos `Loading ...`
    """
    COLOR = 0xa4a4a4

    def __str__(self):
        return 'Loading'

    def __bool__(self):
        return True


class Preparing(Loading):
    """
    Aternos `Preparing ...`
    """
    def __str__(self):
        return 'Preparing'


class Starting(Loading):
    """
    Aternos `Starting ...`

    actions
    - stop
    """
    def __str__(self):
        return 'Starting'


class Restarting(Loading):
    """
    Aternos `Restarting ...`
    """
    def __bool__(self):
        return 'Restarting'


# Falsy loading
class Stopping(Loading):
    """
    Aternos `Stopping ...`
    """
    def __str__(self):
        return 'Stopping'

    def __bool__(self):
        return False


class Saving(Loading):
    """
    Aternos `Saving ...`
    """
    def __str__(self):
        return 'Saving'

    def __bool__(self):
        return False


# Waiting in queue
class WaitingInQueue(BaseStatus):
    """
    actions
    - stop
    - confirm
    """
    COLOR = 0xeb7b59

    def __init__(self, duration: int):
        self.duration = duration

    def __str__(self):
        return f'Waiting in queue {self.duration} minute{"s" if self.duration > 1 else ""} left'

    def __bool__(self):
        return True

    @property
    def est(self) -> str:
        return f'ca. {self.duration} min'

