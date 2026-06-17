"""
appSunPQ/services/check_service.py
Service kiểm tra/tra cứu booking đã giữ chỗ Sun Portal.

Endpoint: POST /normal/manage/retrieve-booking
Payload:  {"pnr_number": "FBX5UK"}
"""

from __future__ import annotations

from typing import Any

from appSunPQ.endpoints import RETRIEVE_BOOKING
from appSunPQ.models.check import CheckResult
from appSunPQ.session_manager import SessionManager
from shared.exceptions import CheckBookingError
from shared.logger import LogPrefix, get_logger

logger = get_logger(LogPrefix.CHECK)


class CheckService:
    """
    Tra cứu thông tin booking theo PNR qua Sun Portal API.

    Endpoint: POST /normal/manage/retrieve-booking
    """

    def __init__(self, session_manager: SessionManager) -> None:
        self._sm = session_manager

    # ── Public API ──────────────────────────────────────────────────────────

    def check_booking(
        self,
        payload: dict[str, Any],
        override_url: str | None = None,
    ) -> CheckResult:
        """
        Tra cứu booking với payload đầy đủ đã build sẵn.

        Args:
            payload:      ``{"pnr_number": "FBX5UK"}``.
            override_url: Ghi đè URL endpoint.

        Returns:
            CheckResult.
        """
        return self._post(payload, override_url)

    def check_booking_simple(
        self,
        pnr: str,
        override_url: str | None = None,
    ) -> CheckResult:
        """
        Tra cứu booking từ PNR — cách ngắn gọn nhất.

        Args:
            pnr:          Mã PNR cần tra cứu (ví dụ "FBX5UK").
            override_url: Ghi đè URL endpoint.

        Returns:
            CheckResult::

                result.pnr             # "FBX5UK"
                result.status          # "OK"
                result.tongbillgiagoc  # 591700
                result.currency        # "KRW"
                result.paymentstatus   # True/False
                result.hanthanhtoan    # "2026-06-16 23:59:59"
                result.chieudi         # list segment chiều đi
                result.chieuve         # list segment chiều về
                result.passengers      # list hành khách

        Example::

            result = client.check_booking_simple("FBX5UK")
            print(result.to_dict())
        """
        payload = {"pnr_number": pnr}
        return self._post(payload, override_url)

    # ── Internal ────────────────────────────────────────────────────────────

    def _post(
        self,
        payload: dict[str, Any],
        override_url: str | None,
    ) -> CheckResult:
        url = override_url or RETRIEVE_BOOKING
        http = self._sm.get_http_client()
        headers = self._sm.get_headers()

        pnr = payload.get("pnr_number", "")
        logger.info(f"Tra cứu booking: pnr={pnr}")
        logger.debug(f"POST {url} payload={payload}")

        try:
            response = http.post(url, headers=headers, json=payload)
            data = response.json()
            result = CheckResult.from_dict(data, status_code=response.status_code)

            logger.info(
                f"Check result: pnr={result.pnr}, status={result.status}, "
                f"paymentstatus={result.paymentstatus}, "
                f"tongbillgiagoc={result.tongbillgiagoc} {result.currency}"
            )
            return result

        except Exception as e:
            logger.exception(f"Check booking thất bại: {e}")
            raise CheckBookingError(f"Check booking thất bại: {e}") from e
