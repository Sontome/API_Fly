"""
core/session.py
VietjetSession — manages authentication, headers, cookies,
request wrapping, retry logic, and token refresh.

Token source: state.json → app_access_token → Bearer header
API layer never touches token directly.
"""

import logging
import time
from pathlib import Path
from typing import Any

import httpx

from core.exceptions import (
    SessionRequestError,
    TokenExpiredError,
    TokenLoadError,
)
from utils.token_loader import get_app_access_token_from_state
logging.getLogger("httpcore").disabled = True
logging.getLogger("httpx").disabled = True
logger = logging.getLogger(__name__)


DEFAULT_HEADERS = {
    "content-type": "application/json",
    "accept": "application/json, text/plain, */*",
    "accept-language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "origin": "https://agent.vietjetair.com",
    "referer": "https://agent.vietjetair.com/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


class VietjetSession:
    """
    Manages the HTTP session for all VietJet API calls.

    Responsibilities:
    - Load Bearer token from state.json
    - Build and cache request headers
    - Wrap GET/POST with retry + auto token refresh on 401
    - Expose clean request() interface to API layer

    Usage:
        session = VietjetSession(state_file="state.json")
        response = session.request("GET", url, params={...})
    """

    def __init__(
        self,
        state_file: str | Path = "state.json",
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self._state_file = Path(state_file)
        self._timeout = timeout
        self._max_retries = max_retries
        self._retry_delay = retry_delay

        # Cached token — loaded lazily
        self._token: str | None = None

        # httpx client — reused across requests (connection pooling)
        self._client: httpx.Client = httpx.Client(
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
        )

        logger.info(f"VietjetSession initialized | state_file={self._state_file}")

    # ------------------------------------------------------------------
    # Token Management
    # ------------------------------------------------------------------

    def load_token_from_state(self, force_reload: bool = False) -> str:
        """
        Load app_access_token from state.json.
        Uses cached value unless force_reload=True.

        Returns:
            Bearer token string.

        Raises:
            TokenLoadError: If token cannot be found.
        """
        if self._token and not force_reload:
            logger.debug("Using cached bearer token")
            return self._token

        logger.info(f"Loading token from: {self._state_file}")
        token = get_app_access_token_from_state(self._state_file)

        if not token:
            raise TokenLoadError(
                f"app_access_token not found in {self._state_file}. "
                "Ensure the state.json is up-to-date."
            )

        self._token = token
        logger.info("Bearer token loaded and cached successfully")
        return self._token

    def invalidate_token(self) -> None:
        """Clear cached token to force reload on next request."""
        logger.debug("Invalidating cached token")
        self._token = None

    # ------------------------------------------------------------------
    # Header Management
    # ------------------------------------------------------------------

    def build_headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """
        Build request headers with Authorization injected.

        Args:
            extra: Optional extra headers to merge.

        Returns:
            Complete headers dict.
        """
        token = self.load_token_from_state()

        headers = {
            **DEFAULT_HEADERS,
            "authorization": f"Bearer {token}",
        }

        if extra:
            headers.update(extra)

        return headers

    # ------------------------------------------------------------------
    # Request Wrapper
    # ------------------------------------------------------------------

    def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Perform an HTTP request with automatic retry and token refresh.

        - On 401: reload token from state.json, rebuild headers, retry once.
        - On other errors: retry up to max_retries with delay.

        Args:
            method:        HTTP method ("GET" or "POST").
            url:           Full request URL.
            params:        Query parameters (for GET).
            json:          JSON body (for POST).
            extra_headers: Additional headers to merge.

        Returns:
            Parsed JSON response as dict.

        Raises:
            TokenExpiredError: If 401 persists after token reload.
            SessionRequestError: If request fails after all retries.
        """
        attempt = 0
        last_error: Exception | None = None

        while attempt < self._max_retries:
            attempt += 1
            headers = self.build_headers(extra_headers)

            try:
                # logger.debug(f"[{method}] {url} | attempt={attempt}")
                response = self._client.request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    params=params,
                    json=json,
                )

                # Token expired — reload and retry immediately (one chance)
                if response.status_code == 401:
                    logger.warning("401 Unauthorized — reloading token from state.json")
                    self.invalidate_token()
                    try:
                        self.load_token_from_state(force_reload=True)
                    except TokenLoadError as e:
                        raise TokenExpiredError(
                            "Token expired and reload failed. "
                            "Please refresh state.json manually."
                        ) from e

                    # Retry immediately with new token (counts as next attempt)
                    continue

                response.raise_for_status()

                data: dict[str, Any] = response.json()
                # logger.debug(f"[{method}] {url} → {response.status_code}")
                return data

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code} on {url}: {e}")
                last_error = SessionRequestError(
                    f"HTTP {e.response.status_code}: {url}",
                    status_code=e.response.status_code,
                    response_text=e.response.text,
                )

            except httpx.TimeoutException as e:
                logger.warning(f"Timeout on {url} (attempt {attempt}): {e}")
                last_error = SessionRequestError(f"Timeout: {url}")

            except httpx.RequestError as e:
                logger.warning(f"Request error on {url} (attempt {attempt}): {e}")
                last_error = SessionRequestError(f"Request error: {url}")

            # Backoff before retry
            if attempt < self._max_retries:
                sleep_time = self._retry_delay * attempt
                logger.debug(f"Retrying in {sleep_time}s...")
                time.sleep(sleep_time)

        raise last_error or SessionRequestError(f"All retries exhausted for {url}")

    # ------------------------------------------------------------------
    # Convenience shorthands
    # ------------------------------------------------------------------

    def get(self, url: str, params: dict[str, Any] | None = None, **kwargs) -> dict[str, Any]:
        return self.request("GET", url, params=params, **kwargs)

    def post(self, url: str, json: dict[str, Any] | None = None, **kwargs) -> dict[str, Any]:
        return self.request("POST", url, json=json, **kwargs)

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()
        logger.info("VietjetSession closed")

    def __enter__(self) -> "VietjetSession":
        return self

    def __exit__(self, *args) -> None:
        self.close()
