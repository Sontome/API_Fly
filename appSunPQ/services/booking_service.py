"""
appSunPQ/services/booking_service.py
Service tạo booking Sun Portal — bước 1 trong luồng 2 bước.

Luồng thật:
    1. POST /normal/create/create-booking
       → BookingPreviewResult (trace_id + booking_status + total_amount)
       → booking_status == "OK"  →  sẵn sàng cho bước 2

    2. POST /normal/create/hold-booking  (HoldService)
       payload: {"trace_id": "FLN...", "option": {"send_email": "Y"}}
       → BookingResult (PNR + booking_code + ...)
"""

from __future__ import annotations

from typing import Any

from appSunPQ.endpoints import CREATE_BOOKING
from appSunPQ.models.booking import (
    BookingPreviewResult,
    ContactInfo,
    Passenger,
    build_booking_payload,
)
from appSunPQ.session_manager import SessionManager
from shared.exceptions import BookingError
from shared.logger import LogPrefix, get_logger

logger = get_logger(LogPrefix.BOOKING)


class BookingService:
    """
    Bước 1 / 2: Gửi thông tin hành trình + hành khách lên Sun Portal,
    nhận về trace_id để xác nhận giữ vé ở bước 2 (HoldService).

    Endpoint: POST /normal/create/create-booking
    """

    def __init__(self, session_manager: SessionManager) -> None:
        self._sm = session_manager

    # ── Public API ──────────────────────────────────────────────────────────

    def create_booking(
        self,
        payload: dict[str, Any],
        override_url: str | None = None,
    ) -> BookingPreviewResult:
        """
        Gửi payload đầy đủ đã build sẵn, nhận về BookingPreviewResult.

        Args:
            payload:      Payload chuẩn Sun Portal. Dùng ``build_booking_payload``
                          từ ``appSunPQ.models.booking`` để tạo, hoặc truyền dict thô.
            override_url: Ghi đè URL endpoint (staging/test).

        Returns:
            BookingPreviewResult chứa trace_id, booking_status, total_amount.
            Dùng ``preview.trace_id`` để gọi ``hold_simple()`` tiếp theo.

        Raises:
            BookingError: Nếu request thất bại hoặc exception.
        """
        return self._post(payload, override_url)

    def create_booking_simple(
        self,
        list_itinerary: list[dict[str, Any]],
        list_passenger: list[Passenger] | list[dict[str, Any]],
        contact_info: ContactInfo | dict[str, Any],
        promo_code: str = "",
        corporate_code: str = "",
        currency: str = "KRW",
        override_url: str | None = None,
    ) -> BookingPreviewResult:
        """
        Bước 1: Tạo booking preview từ tham số ngắn gọn — tự build payload.

        ``trip_type`` suy ra tự động:
        - "RT"  nếu list_itinerary có cả trip_id=1 và trip_id=2.
        - "OW"  nếu chỉ có trip_id=1.

        Args:
            list_itinerary:  Danh sách segment, ghép từ chiều đi + chiều về.
                             Lấy từ ``formatted["body"][i]["chiều_đi"]["list_itinerary"]``
                             (+ ``["chiều_về"]["list_itinerary"]`` nếu RT).
            list_passenger:  Danh sách hành khách (list[Passenger] hoặc list[dict]).
            contact_info:    Thông tin liên hệ (ContactInfo hoặc dict).
            promo_code:      Mã khuyến mãi.
            corporate_code:  Mã hợp đồng công ty.
            currency:        Tiền tệ ("KRW", "VND", ...).
            override_url:    Ghi đè URL endpoint.

        Returns:
            BookingPreviewResult.
            - ``preview.is_confirmed`` → True khi booking_status == "OK"
            - ``preview.trace_id``     → truyền vào ``hold_simple()``
            - ``preview.total_amount`` → tổng tiền cần thanh toán

        Example::

            body = search_result.formatted["body"][0]
            itin = (
                body["chiều_đi"]["list_itinerary"]
                + body["chiều_về"]["list_itinerary"]
            )

            preview = service.create_booking_simple(
                list_itinerary=itin,
                list_passenger=[
                    Passenger(pax_id=1, type="ADULT",
                              first_name="XUAN SON", last_name="TRINH"),
                ],
                contact_info=ContactInfo(
                    email="son@example.com",
                    phone_number="+84985422486",
                    full_name="Mr Son HVA",
                ),
            )

            if preview.is_confirmed:
                hold = hold_service.hold_simple(preview.trace_id)
                print(hold.pnr)
        """
        payload = build_booking_payload(
            list_itinerary=list_itinerary,
            list_passenger=list_passenger,
            contact_info=contact_info,
            promo_code=promo_code,
            corporate_code=corporate_code,
            currency=currency,
        )
        return self._post(payload, override_url)

    # ── Internal ────────────────────────────────────────────────────────────

    def _post(
        self,
        payload: dict[str, Any],
        override_url: str | None,
    ) -> BookingPreviewResult:
        url = override_url or CREATE_BOOKING
        http = self._sm.get_http_client()
        headers = self._sm.get_headers()

        trip_type = payload.get("option", {}).get("trip_type", "?")
        pax_count = len(payload.get("list_passenger", []))
        seg_count = len(payload.get("list_itinerary", []))
        logger.info(
            f"Create booking (bước 1): trip_type={trip_type}, "
            f"segments={seg_count}, passengers={pax_count}"
        )
        logger.debug(f"POST {url} payload={payload}")

        try:
            response = http.post(url, headers=headers, json=payload)
            data = response.json()
            preview = BookingPreviewResult.from_dict(data)

            logger.info(
                f"Preview result: success={preview.success}, "
                f"booking_status={preview.booking_status}, "
                f"trace_id={preview.trace_id}, "
                f"total={preview.total_amount} {preview.currency}, "
                f"is_confirmed={preview.is_confirmed}"
            )

            if not preview.success:
                raise BookingError(
                    f"Create booking trả về success=False: {preview.error}",
                    code="CREATE_BOOKING_FAILED",
                )

            return preview

        except BookingError:
            raise
        except Exception as e:
            logger.exception(f"Create booking thất bại: {e}")
            raise BookingError(f"Create booking thất bại: {e}") from e
