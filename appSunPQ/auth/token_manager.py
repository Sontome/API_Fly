"""
appSunPQ/auth/token_manager.py
Quản lý access_token và refresh_token từ state file.
"""

from __future__ import annotations

from typing import Any

from appSunPQ.constants import STATE_FILE
from shared.exceptions import TokenRefreshError
from shared.logger import LogPrefix, get_logger
from shared.storage import read_json, write_json

logger = get_logger(LogPrefix.AUTH)


class TokenManager:
    """
    Đọc, lưu và cung cấp token từ state file.

    Attributes:
        state_file: Đường dẫn tới file state JSON.
    """

    def __init__(self, state_file: str = STATE_FILE) -> None:
        self.state_file = state_file
        self._state: dict[str, Any] = {}

    def load(self) -> None:
        """Đọc state file vào bộ nhớ."""
        self._state = read_json(self.state_file)
        logger.debug("Đã load state vào TokenManager")

    def get_access_token(self) -> str:
        """
        Trả về access_token hiện tại.

        Returns:
            Access token string.
        """
        token = self._state.get("access_token", "")
        if not token:
            logger.warning("token trống trong state")
        return token
    def get_cookie(self) -> dict[str, str]:
        cookie_list = self._state.get("cookies", [])

        if not cookie_list:
            logger.warning("cookies trống trong state")
            return {}

        return {
            cookie["name"]: cookie["value"]
            for cookie in cookie_list
        }
    def get_refresh_token(self) -> str:
        """
        Trả về refresh_token hiện tại.

        Returns:
            Refresh token string.
        """
        return self._state.get("refresh_token", "")

    def update_tokens(self, access_token: str, refresh_token: str = "") -> None:
        """
        Cập nhật token mới vào state và lưu file.

        Args:
            access_token: Token mới.
            refresh_token: Refresh token mới (optional).
        """
        self._state["access_token"] = access_token
        if refresh_token:
            self._state["refresh_token"] = refresh_token
        write_json(self.state_file, self._state)
        logger.info("Đã cập nhật token vào state file")

    def update_full_state(self, new_state: dict[str, Any]) -> None:
        """
        Ghi đè toàn bộ state (dùng sau khi login lại bằng Playwright).

        Args:
            new_state: State mới từ Playwright login.
        """
        self._state = new_state
        write_json(self.state_file, new_state)
        logger.info("Đã cập nhật toàn bộ state")

    def has_token(self) -> bool:
        """Kiểm tra xem có access_token không."""
        return bool(self._state.get("access_token"))

    @property
    def state(self) -> dict[str, Any]:
        """Trả về state hiện tại (read-only)."""
        return dict(self._state)
