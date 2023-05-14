class _AIKnowsError(Exception):
    """Base class for exceptions in this module."""

    pass


class AIKnowsTaskError(_AIKnowsError):
    """Exception raised by assistant when task can't be complete."""

    def __init__(self, *args: object, error_cause: bool = False) -> None:
        super().__init__(*args)

        self.error_cause = error_cause
