"""
appSunPQ/auth/cookie_manager.py
Khôi phục cookies từ state file và inject vào requests.Session.
"""

from __future__ import annotations

from typing import Any

import requests

from shared.logger import LogPrefix, get_logger

logger = get_logger(LogPrefix.SESSION)


class CookieManager:
    """
    Đọc cookies từ state file và inject vào requests.Session.

    Sun Portal yêu cầu đồng thời:
    - Authorization: Bearer <token>
    - Cookie browser session

    Do đó KHÔNG được bỏ qua bước inject cookie.
    """

    def __init__(self, cookies: list[dict[str, Any]]) -> None:
        """
        Args:
            cookies: Danh sách cookie dạng dict từ Playwright.
                     Mỗi cookie có: name, value, domain, path, expires, ...
        """
        self._cookies = cookies

    @classmethod
    def from_state(cls, state: dict[str, Any]) -> "CookieManager":
        """
        Tạo CookieManager từ state dict.

        Args:
            state: Dict state đọc từ sunportal_state.json.

        Returns:
            CookieManager instance.
        """
        cookies = state.get("cookies", [])
        return cls(cookies)

    def inject_into_session(self, session: requests.Session) -> None:
        """
        Inject toàn bộ cookies vào requests.Session.

        Args:
            session: requests.Session cần inject.
        """
        injected = 0
        skipped = 0

        for cookie in self._cookies:
            name = cookie.get("name", "").strip()
            value = cookie.get("value", "").strip()
            domain = cookie.get("domain", "")
            path = cookie.get("path", "/")

            if not name or not value:
                skipped += 1
                continue

            # Playwright trả domain dạng ".sunportal.com.vn"
            # requests.Session.cookies.set cần domain không có dấu chấm đầu
            clean_domain = domain.lstrip(".")

            session.cookies.set(
                name=name,
                value=value,
                domain=clean_domain,
                path=path,
            )
            injected += 1

        logger.info(f"Inject cookies: {injected} thành công, {skipped} bỏ qua")

    def get_cookie_header(self) -> str:
        """
        Build Cookie header string từ danh sách cookies.

        Returns:
            String dạng "name1=value1; name2=value2".
        """
        parts = []
        for cookie in self._cookies:
            name = cookie.get("name", "")
            value = cookie.get("value", "")
            if name and value:
                parts.append(f"{name}={value}")
        return "; ".join(parts)

    def count(self) -> int:
        """Trả về số lượng cookie."""
        return len(self._cookies)

    def filter_by_domain(self, domain: str) -> list[dict[str, Any]]:
        """
        Lọc cookie theo domain.

        Args:
            domain: Domain cần lọc (ví dụ: "sunportal.com.vn").

        Returns:
            Danh sách cookie khớp domain.
        """
        return [
            c for c in self._cookies
            if domain in c.get("domain", "")
        ]
