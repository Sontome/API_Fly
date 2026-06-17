"""
shared/logger.py
Logger dùng chung với prefix phân loại rõ ràng.
"""

import logging
import sys
try:
    from enum import StrEnum
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):
        pass


class LogPrefix(StrEnum):
    AUTH = "AUTH"
    SESSION = "SESSION"
    HTTP = "HTTP"
    SEARCH = "SEARCH"
    HOLD = "HOLD"
    BOOKING = "BOOKING"
    CHECK = "CHECK"
    STATE = "STATE"
    GENERAL = "GENERAL"


class PrefixedLogger:
    """Logger wrapper tự động thêm prefix vào message."""

    def __init__(self, prefix: LogPrefix, base_logger: logging.Logger) -> None:
        self._prefix = prefix
        self._logger = base_logger

    def _fmt(self, message: str) -> str:
        return f"[{self._prefix}] {message}"

    def debug(self, message: str, *args, **kwargs) -> None:
        self._logger.debug(self._fmt(message), *args, **kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        self._logger.info(self._fmt(message), *args, **kwargs)

    def warning(self, message: str, *args, **kwargs) -> None:
        self._logger.warning(self._fmt(message), *args, **kwargs)

    def error(self, message: str, *args, **kwargs) -> None:
        self._logger.error(self._fmt(message), *args, **kwargs)

    def exception(self, message: str, *args, **kwargs) -> None:
        self._logger.exception(self._fmt(message), *args, **kwargs)


def _setup_root_logger(level: int = logging.INFO) -> logging.Logger:
    """Thiết lập root logger với format chuẩn."""
    logger = logging.getLogger("sunportal")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = False
    return logger


_root = _setup_root_logger()


def get_logger(prefix: LogPrefix) -> PrefixedLogger:
    """Trả về PrefixedLogger theo prefix cho trước."""
    return PrefixedLogger(prefix, _root)


def set_log_level(level: int) -> None:
    """Thay đổi log level toàn cục."""
    _root.setLevel(level)
