"""
core/exceptions.py
Custom exceptions for VietJet Change Price module.
"""


class VietjetBaseError(Exception):
    """Base exception for all VietJet errors."""
    pass


class TokenLoadError(VietjetBaseError):
    """Raised when bearer token cannot be loaded from state.json."""
    pass


class TokenExpiredError(VietjetBaseError):
    """Raised when the API returns 401 Unauthorized."""
    pass


class SessionRequestError(VietjetBaseError):
    """Raised when an HTTP request fails after all retries."""

    def __init__(self, message: str, status_code: int | None = None, response_text: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class ApiResponseError(VietjetBaseError):
    """Raised when API returns unexpected/malformed response."""

    def __init__(self, message: str, raw_response: dict | None = None):
        super().__init__(message)
        self.raw_response = raw_response


class QuotationError(VietjetBaseError):
    """Raised when quotation flow fails."""
    pass
