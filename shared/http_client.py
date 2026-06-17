"""
shared/http_client.py
HTTP client dùng chung: requests.Session với retry, timeout, logging.
"""

from __future__ import annotations

import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from shared.exceptions import HttpRequestError
from shared.logger import LogPrefix, get_logger

logger = get_logger(LogPrefix.HTTP)

DEFAULT_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 0.5
RETRY_STATUS_CODES = (500, 502, 503, 504)


def build_session(
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    timeout: int = DEFAULT_TIMEOUT,
) -> requests.Session:
    """
    Tạo requests.Session với retry và timeout cấu hình sẵn.

    Args:
        max_retries: Số lần retry tối đa.
        backoff_factor: Hệ số backoff giữa các lần retry.
        timeout: Timeout mặc định (giây).

    Returns:
        requests.Session đã được cấu hình.
    """
    session = requests.Session()

    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=RETRY_STATUS_CODES,
        allowed_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # Lưu timeout vào session để dùng sau
    session._default_timeout = timeout  # type: ignore[attr-defined]

    logger.debug(f"Tạo HTTP session: max_retries={max_retries}, timeout={timeout}s")
    return session


class HttpClient:
    """
    HTTP client wrapper với logging và xử lý lỗi.

    Attributes:
        session: requests.Session đã cấu hình.
        timeout: Timeout mặc định cho mỗi request.
    """

    def __init__(
        self,
        session: requests.Session | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self.timeout = timeout
        self.session = session or build_session(max_retries=max_retries, timeout=timeout)

    def get(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        **kwargs,
    ) -> requests.Response:
        """
        HTTP GET.

        Args:
            url: URL endpoint.
            headers: HTTP headers.
            params: Query parameters.
            **kwargs: Các tham số truyền vào requests.

        Returns:
            requests.Response

        Raises:
            HttpRequestError: Nếu request thất bại.
        """
        return self._request("GET", url, headers=headers, params=params, **kwargs)

    def post(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        data: Any = None,
        **kwargs,
    ) -> requests.Response:
        """
        HTTP POST.

        Args:
            url: URL endpoint.
            headers: HTTP headers.
            json: Payload JSON.
            data: Payload raw data.
            **kwargs: Các tham số truyền vào requests.

        Returns:
            requests.Response

        Raises:
            HttpRequestError: Nếu request thất bại.
        """
        return self._request("POST", url, headers=headers, json=json, data=data, **kwargs)

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Thực hiện HTTP request với logging.

        Args:
            method: HTTP method (GET, POST, v.v.).
            url: URL endpoint.
            **kwargs: Các tham số truyền vào requests.

        Returns:
            requests.Response

        Raises:
            HttpRequestError: Nếu request thất bại.
        """
        timeout = kwargs.pop("timeout", self.timeout)
        start = time.perf_counter()

        logger.debug(f"{method} {url}")

        try:
            response = self.session.request(method, url, timeout=timeout, **kwargs)
            elapsed = time.perf_counter() - start
            logger.info(
                f"{method} {url} → {response.status_code} ({elapsed:.2f}s)"
            )

            if response.status_code == 401:
                raise HttpRequestError(
                    f"Unauthorized (401): {url}",
                    status_code=401,
                    code="UNAUTHORIZED",
                )

            if response.status_code >= 400:
                raise HttpRequestError(
                    f"HTTP {response.status_code}: {url} → {response.text[:200]}",
                    status_code=response.status_code,
                )

            return response

        except HttpRequestError:
            raise
        except requests.exceptions.ConnectionError as e:
            raise HttpRequestError(f"Connection error: {url}: {e}", code="CONNECTION_ERROR") from e
        except requests.exceptions.Timeout as e:
            raise HttpRequestError(f"Timeout: {url}: {e}", code="TIMEOUT") from e
        except requests.exceptions.RequestException as e:
            raise HttpRequestError(f"Request failed: {url}: {e}") from e

    def inject_cookies(self, cookies: list[dict[str, Any]]) -> None:
        """
        Inject danh sách cookie vào session.

        Args:
            cookies: Danh sách cookie dạng dict (từ Playwright).
        """
        for cookie in cookies:
            name = cookie.get("name", "")
            value = cookie.get("value", "")
            domain = cookie.get("domain", "")
            path = cookie.get("path", "/")

            if not name or not value:
                continue

            # Xử lý domain bắt đầu bằng dấu chấm
            clean_domain = domain.lstrip(".")

            self.session.cookies.set(
                name=name,
                value=value,
                domain=clean_domain,
                path=path,
            )

        logger.debug(f"Đã inject {len(cookies)} cookies vào session")

    def set_default_headers(self, headers: dict[str, str]) -> None:
        """
        Thiết lập default headers cho toàn bộ session.

        Args:
            headers: Dict headers cần thiết lập.
        """
        self.session.headers.update(headers)
        logger.debug(f"Cập nhật default headers: {list(headers.keys())}")
