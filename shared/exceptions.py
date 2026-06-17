"""
shared/exceptions.py
Các exception dùng chung cho toàn bộ project.
"""


class BaseAppException(Exception):
    """Base exception cho toàn bộ ứng dụng."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, code={self.code!r})"


class AuthenticationError(BaseAppException):
    """Lỗi xác thực - token hết hạn, sai credentials, v.v."""


class SessionExpiredError(AuthenticationError):
    """Session đã hết hạn, cần login lại."""


class TokenRefreshError(AuthenticationError):
    """Không thể refresh token."""


class LoginFailedError(AuthenticationError):
    """Đăng nhập thất bại."""


class HttpRequestError(BaseAppException):
    """Lỗi HTTP request."""

    def __init__(self, message: str, status_code: int | None = None, code: str | None = None) -> None:
        super().__init__(message, code)
        self.status_code = status_code


class StateFileError(BaseAppException):
    """Lỗi đọc/ghi state file."""


class SearchError(BaseAppException):
    """Lỗi khi tìm kiếm chuyến bay."""


class HoldError(BaseAppException):
    """Lỗi khi giữ chỗ."""


class BookingError(BaseAppException):
    """Lỗi khi tạo booking."""


class CheckBookingError(BaseAppException):
    """Lỗi khi truy vấn/kiểm tra booking."""


class ConfigurationError(BaseAppException):
    """Lỗi cấu hình - thiếu env var, v.v."""
