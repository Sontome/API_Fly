"""
appSunPQ/services/hold_service.py
Service giữ chỗ (hold booking) Sun Portal — bước 2 sau create-booking.

Endpoint: POST /normal/create/hold-booking

Payload thật::

    {
        "trace_id": "FLN202606151333301781505210793301563",
        "option":   {"send_email": "Y"}
    }

Luồng đúng:
    1. BookingService.create_booking_simple(...)  → BookingPreviewResult (trace_id)
    2. HoldService.hold_simple(trace_id)          → BookingResult (PNR)
"""

from __future__ import annotations

from typing import Any

from appSunPQ.endpoints import HOLD_BOOKING
from appSunPQ.models.booking import BookingResult, build_hold_payload
from appSunPQ.session_manager import SessionManager
from shared.exceptions import HoldError
from shared.logger import LogPrefix, get_logger

logger = get_logger(LogPrefix.HOLD)


class HoldService:
    """
    Giữ chỗ chuyến bay qua Sun Portal API — bước 2 sau create-booking.

    Endpoint: POST /normal/create/hold-booking
    """

    def __init__(self, session_manager: SessionManager) -> None:
        self._sm = session_manager

    # ── Public API ──────────────────────────────────────────────────────────

    def hold(
        self,
        payload: dict[str, Any],
        override_url: str | None = None,
    ) -> BookingResult:
        """
        Giữ chỗ với payload đầy đủ đã build sẵn.

        Args:
            payload:      Payload hold-booking. Dùng ``build_hold_payload(trace_id)``
                          để tạo, hoặc truyền thẳng dict::

                              {"trace_id": "FLN...", "option": {"send_email": "Y"}}

            override_url: Ghi đè URL endpoint.

        Returns:
            BookingResult chứa pnr, expiration_date, total_amount, booking_status.

        Raises:
            HoldError: Nếu request thất bại.
        """
        return self._post(payload, override_url)

    def hold_simple(
        self,
        trace_id: str,
        send_email: bool = True,
        override_url: str | None = None,
    ) -> BookingResult:
        """
        Giữ chỗ từ trace_id — tự build payload, cách ngắn gọn nhất.

        Gọi ngay sau ``create_booking_simple`` khi ``preview.is_confirmed == True``.

        Args:
            trace_id:     trace_id lấy từ ``BookingPreviewResult.trace_id``.
            send_email:   Gửi email xác nhận cho khách (mặc định True).
            override_url: Ghi đè URL endpoint.

        Returns:
            BookingResult chứa pnr, expiration_date, total_amount, booking_status.

        Example::

            preview = booking_service.create_booking_simple(...)
            if preview.is_confirmed:
                hold = hold_service.hold_simple(preview.trace_id)
                print(hold.pnr)
        """
        payload = build_hold_payload(trace_id=trace_id, send_email=send_email)
        return self._post(payload, override_url)

    # ── Internal ────────────────────────────────────────────────────────────

    def _post(
        self,
        payload: dict[str, Any],
        override_url: str | None,
    ) -> BookingResult:
        url = override_url or HOLD_BOOKING
        http = self._sm.get_http_client()
        headers = self._sm.get_headers()

        trace_id = payload.get("trace_id", "")
        send_email = payload.get("option", {}).get("send_email", "?")
        logger.info(f"Hold booking: trace_id={trace_id}, send_email={send_email}")
        logger.debug(f"POST {url} payload={payload}")

        try:
            response = http.post(url, headers=headers, json=payload)
            data = response.json()
            result = BookingResult.from_dict(data, status_code=response.status_code)

            logger.info(
                f"Hold result: success={result.success}, "
                f"pnr={result.pnr}, "
                f"booking_status={result.booking_status}, "
                f"expiration_date={result.expiration_date}, "
                f"total_amount={result.total_amount} {result.currency}, "
                f"is_held={result.is_held}"
            )
            return result

        except Exception as e:
            logger.exception(f"Hold booking thất bại: {e}")
            raise HoldError(f"Hold booking thất bại: {e}") from e
