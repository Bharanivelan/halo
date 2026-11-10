"""Error classes that drive retry policy (SYSTEM_ARCHITECTURE §7.4)."""


class TransientError(Exception):
    """Timeouts, 429s, 5xx, connection resets → retry with backoff."""

    def __init__(self, message: str, retry_after_s: float | None = None):
        super().__init__(message)
        self.retry_after_s = retry_after_s


class PermanentError(Exception):
    """Bad input, 404, robots disallow → fail without retry. Message is shown to users."""


class BudgetExceeded(Exception):
    """The next paid call would exceed the job's budget cap → pause the job."""
