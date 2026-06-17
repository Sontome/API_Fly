"""
appSunPQ/session_manager.py
Khôi phục session đầy đủ: token + cookies.
Tự động login lại nếu session hết hạn.
"""

from __future__ import annotations

from typing import Any

import requests

from appSunPQ.auth.cookie_manager import CookieManager
from appSunPQ.auth.playwright_login import PlaywrightLoginService
from appSunPQ.auth.token_manager import TokenManager
from appSunPQ.constants import STATE_FILE
from appSunPQ.endpoints import CHECK_ACCOUNT_FUND
from shared.exceptions import SessionExpiredError
from shared.http_client import HttpClient, build_session
from shared.logger import LogPrefix, get_logger

logger = get_logger(LogPrefix.SESSION)


class HeaderBuilder:
    """
    Build HTTP headers chuẩn cho Sun Portal API.
    Token được lấy động từ TokenManager — không hardcode.
    """

    BASE_HEADERS: dict[str, str] = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "content-type": "application/json",
        "origin": "https://sunportal.com.vn",
        "referer": "https://sunportal.com.vn/",
    }

    def __init__(self, token_manager: TokenManager) -> None:
        self._tm = token_manager

    def build(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """
        Build headers đầy đủ với Bearer token hiện tại.

        Args:
            extra: Headers bổ sung (override nếu trùng key).

        Returns:
            Dict headers hoàn chỉnh.
        """
        token = self._tm.get_access_token()
        headers = {
            **self.BASE_HEADERS,
            "authorization": f"Bearer {token}",
        }
        
        if extra:
            headers.update(extra)
        return headers

    def build_for_get(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """Build headers cho GET request."""
        get_headers = {k: v for k, v in self.BASE_HEADERS.items() if k != "content-type"}
        token = self._tm.get_access_token()
        cookies = self._tm.get_cookie()
        
        headers = {
            **get_headers,
            "authorization": f"Bearer {token}"
        }
        # print(headers)
        if extra:
            headers.update(extra)
        return headers,cookies


class SessionManager:
    """
    Quản lý toàn bộ session cho Sun Portal.

    Luồng:
    1. Đọc state file.
    2. Nạp token vào TokenManager.
    3. Nạp cookie vào CookieManager.
    4. Khôi phục requests.Session.
    5. Kiểm tra token còn hoạt động (check-account-fund).
    6. Nếu hết hạn → login lại bằng Playwright → cập nhật state.
    """

    def __init__(
        self,
        state_file: str = STATE_FILE,
        headless: bool = False,
    ) -> None:
        self.state_file = state_file
        self.headless = headless

        self.token_manager = TokenManager(state_file)
        self._raw_session = build_session()
        self.http_client = HttpClient(session=self._raw_session)
        self.header_builder = HeaderBuilder(self.token_manager)
        self._ready = False

    def initialize(self) -> None:
        """
        Khởi tạo session đầy đủ.

        - Nếu state file tồn tại và token còn hạn → restore session.
        - Nếu không → tự động login lại bằng Playwright.
        """
        logger.info("Khởi tạo SessionManager...")
        self.token_manager.load()

        if not self.token_manager.has_token():
            logger.info("Không có token, tiến hành đăng nhập...")
            self._login_with_playwright()
        else:
            self._restore_session()
            if not self._is_session_valid():
                logger.warning("Session đã hết hạn, đăng nhập lại...")
                self._login_with_playwright()

        self._ready = True
        logger.info("SessionManager sẵn sàng.")

    def _restore_session(self) -> None:
        """Inject cookies và header mặc định vào session."""
        state = self.token_manager.state
        cookie_manager = CookieManager.from_state(state)
        cookie_manager.inject_into_session(self._raw_session)

        default_headers = self.header_builder.build()
        self.http_client.set_default_headers(default_headers)

        logger.info(
            f"Session restored: {cookie_manager.count()} cookies, "
            f"token={'***' + self.token_manager.get_access_token()[-8:] if self.token_manager.get_access_token() else 'EMPTY'}"
        )

    def _is_session_valid(self) -> bool:
        """
        Kiểm tra session còn hợp lệ bằng cách gọi check-account-fund.

        Returns:
            True nếu session OK, False nếu đã hết hạn.
        """
        logger.debug(f"Kiểm tra session tại: {CHECK_ACCOUNT_FUND}")
        try:

            headers,cookies = self.header_builder.build_for_get()
            print(cookies)
            print(type(cookies))
            self.http_client.get(CHECK_ACCOUNT_FUND, headers=headers,cookies=cookies)
            logger.info("Session hợp lệ.")
            return True
        except Exception as e:
            logger.warning(f"Session không hợp lệ: {e}")
            return False

    def _login_with_playwright(self) -> None:
        """Đăng nhập lại bằng Playwright và cập nhật state."""
        login_service = PlaywrightLoginService(
            state_file=self.state_file,
            headless=self.headless,
        )
        new_state = login_service.login()
        self.token_manager.update_full_state(new_state)

        # Reset session sau khi login
        self._raw_session = build_session()
        self.http_client = HttpClient(session=self._raw_session)
        self.header_builder = HeaderBuilder(self.token_manager)

        self._restore_session()

    def ensure_ready(self) -> None:
        """
        Đảm bảo session đang hoạt động.
        Gọi trước mỗi request quan trọng.
        """
        if not self._ready:
            self.initialize()

    def get_http_client(self) -> HttpClient:
        """Trả về HttpClient đã cấu hình sẵn."""
        self.ensure_ready()
        return self.http_client

    def get_headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """Build và trả về headers hiện tại."""
        return self.header_builder.build(extra)

    def get_get_headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """Build và trả về headers cho GET request."""
        return self.header_builder.build_for_get(extra)
