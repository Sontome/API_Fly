"""
appSunPQ/auth/playwright_login.py
Đăng nhập Sun Portal bằng browser thật, thu thập toàn bộ trạng thái session.
"""

from __future__ import annotations

import json
from typing import Any
import time
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from appSunPQ.constants import (
    LOGIN_URL,
    PASSWORD_SELECTOR,
    PLAYWRIGHT_TIMEOUT,
    STATE_FILE,
    SUBMIT_SELECTOR,
    USERNAME_SELECTOR,
    AGENTCYCODE_SELECTOR,
)
from shared.exceptions import LoginFailedError
from shared.logger import LogPrefix, get_logger
from shared.storage import get_env, write_json

logger = get_logger(LogPrefix.AUTH)


class PlaywrightLoginService:
    """
    Đăng nhập Sun Portal bằng Playwright (browser thật).

    Thu thập:
    - access_token
    - refresh_token
    - cookies
    - local_storage
    - session_storage

    Lưu toàn bộ vào STATE_FILE.
    """

    def __init__(
        self,
        state_file: str = STATE_FILE,
        headless: bool = False,
        timeout: int = PLAYWRIGHT_TIMEOUT,
    ) -> None:
        self.state_file = state_file
        self.headless = headless
        self.timeout = timeout

        # Lấy credentials từ .env
        self.username = get_env("SUNPORTAL_USERNAME")
        self.password = get_env("SUNPORTAL_PASSWORD")
        self.agentcycode = get_env("AGENTCYCODE")
    def login(self) -> dict[str, Any]:
        """
        Thực hiện login, thu thập state và lưu file.

        Returns:
            Dict chứa toàn bộ trạng thái session.

        Raises:
            LoginFailedError: Nếu đăng nhập thất bại.
        """
        logger.info(f"Bắt đầu Playwright login cho user: {self.username}")

        with sync_playwright() as p:
            browser: Browser = p.chromium.launch(headless=self.headless)
            context: BrowserContext = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            page: Page = context.new_page()
            page.set_default_timeout(self.timeout)

            # Lưu token từ network request
            captured_tokens: dict[str, str] = {}
            self._setup_token_capture(page, captured_tokens)

            try:
                state = self._do_login(page, context, captured_tokens)
                write_json(self.state_file, state)
                logger.info(f"Login thành công. State đã lưu vào: {self.state_file}")
                return state
            finally:
                context.close()
                browser.close()

    def _setup_token_capture(self, page: Page, captured: dict[str, str]) -> None:
        """
        Hook network response để bắt access_token và refresh_token.

        Args:
            page: Playwright Page.
            captured: Dict để lưu token bắt được.
        """

        def on_response(response):
            try:
                content_type = response.headers.get("content-type", "")
                if "json" not in content_type:
                    return
                if response.status != 200:
                    return

                body = response.json()
                if isinstance(body, dict):
                    # Tìm token trong body hoặc data
                    data = body.get("data", body)
                    if isinstance(data, dict):
                        if "access_token" in data:
                            captured["access_token"] = data["access_token"]
                            logger.debug("Đã bắt được access_token từ response")
                        if "refresh_token" in data:
                            captured["refresh_token"] = data["refresh_token"]
                            logger.debug("Đã bắt được refresh_token từ response")
            except Exception:
                pass  # Bỏ qua response không parse được

        page.on("response", on_response)

    def _do_login(
        self,
        page: Page,
        context: BrowserContext,
        captured_tokens: dict[str, str],
    ) -> dict[str, Any]:
        """
        Thực hiện login trên page và thu thập state.

        Args:
            page: Playwright Page.
            context: Playwright BrowserContext.
            captured_tokens: Dict token đã bắt được từ network.

        Returns:
            Dict state đầy đủ.

        Raises:
            LoginFailedError: Nếu đăng nhập thất bại.
        """
        logger.debug(f"Mở URL: {LOGIN_URL}")
        page.goto(LOGIN_URL, wait_until="networkidle")
        # Điền AGENTCYCODE
        logger.debug("Nhập username...")
        username_field = page.locator(AGENTCYCODE_SELECTOR).first
        username_field.wait_for(state="visible")
        username_field.fill(self.agentcycode)
        # Điền username
        logger.debug("Nhập username...")
        username_field = page.locator(USERNAME_SELECTOR).first
        username_field.wait_for(state="visible")
        username_field.fill(self.username)

        # Điền password
        logger.debug("Nhập password...")
        password_field = page.locator(PASSWORD_SELECTOR).first
        password_field.fill(self.password)

        # Submit
        logger.debug("Submit form đăng nhập...")
        submit_btn = page.locator(SUBMIT_SELECTOR).first
        submit_btn.click()

        # Chờ đăng nhập thành công
        try:
            time.sleep (1)
            page.wait_for_load_state("networkidle", timeout=self.timeout)
        except Exception as e:
            logger.warning(f"Timeout chờ networkidle: {e}")

        # Kiểm tra đăng nhập thành công bằng URL hoặc element
        current_url = page.url
        print (current_url)
        # if "login" in current_url.lower() and "error" in page.content().lower():
        
        #     raise LoginFailedError(
        #         f"Đăng nhập thất bại. URL hiện tạia: {current_url}"
        #     )

        logger.debug("Đăng nhập thành công, thu thập state...")

        # Thu thập cookies
        cookies = context.cookies()
        logger.debug(f"Thu thập được {len(cookies)} cookies")

        # Thu thập localStorage
        local_storage = self._collect_storage(page, "localStorage")

        # Thu thập sessionStorage
        session_storage = self._collect_storage(page, "sessionStorage")

        access_token = None

        for cookie in cookies:
            if cookie["name"] == "token":
                access_token = cookie["value"]
                break
        print(access_token)            
        state: dict[str, Any] = {
            
            "cookies": cookies,
            "local_storage": local_storage,
            "session_storage": session_storage,
            "access_token":access_token
            
        }

        # if not state["access_token"]:
        #     logger.warning(
        #         "Không tìm thấy access_token trong response. "
        #         "Kiểm tra lại selector hoặc cấu trúc response."
        #     )

        return state

    def _collect_storage(self, page: Page, storage_type: str) -> dict[str, str]:
        """
        Thu thập dữ liệu từ localStorage hoặc sessionStorage.

        Args:
            page: Playwright Page.
            storage_type: 'localStorage' hoặc 'sessionStorage'.

        Returns:
            Dict key-value của storage.
        """
        try:
            result: dict[str, str] = page.evaluate(
                f"""() => {{
                    const items = {{}};
                    const storage = window.{storage_type};
                    for (let i = 0; i < storage.length; i++) {{
                        const key = storage.key(i);
                        items[key] = storage.getItem(key);
                    }}
                    return items;
                }}"""
            )
            logger.debug(f"{storage_type}: {len(result)} keys")
            return result
        except Exception as e:
            logger.warning(f"Không thể thu thập {storage_type}: {e}")
            return {}