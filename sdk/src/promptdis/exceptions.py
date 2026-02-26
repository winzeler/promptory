"""Promptdis SDK exceptions."""


class PromptdisError(Exception):
    """Base exception for Promptdis SDK."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class NotFoundError(PromptdisError):
    """Prompt or resource not found."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class AuthenticationError(PromptdisError):
    """Invalid or missing API key."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class RateLimitError(PromptdisError):
    """Rate limit exceeded."""

    def __init__(self, retry_after: int | None = None):
        msg = "Rate limit exceeded"
        if retry_after:
            msg += f". Retry after {retry_after}s"
        super().__init__(msg, status_code=429)
        self.retry_after = retry_after
