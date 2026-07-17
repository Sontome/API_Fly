"""
appSunPQ/client.py
SunPortalClient — facade duy nhất để tương tác với Sun Portal.

Luồng đầy đủ:
    Playwright Login
    → Save State (sunportal_state.json)
    → Restore Session → Inject Cookies + Bearer Token

    → search_simple(...)              → SearchResponse
    → create_booking_simple(...)      → BookingPreviewResult  (có trace_id)
    → hold_simple(preview.trace_id)   → BookingResult         (có PNR)
"""

from __future__ import annotations

from typing import Any

from appSunPQ.constants import STATE_FILE
from appSunPQ.models.booking import (
    BookingPreviewResult,
    BookingResult,
    ContactInfo,
    Passenger,
)
from appSunPQ.models.check import CheckResult
from appSunPQ.models.confirm_price import ConfirmPriceResult
from appSunPQ.models.minfare import MinFareResult
from appSunPQ.models.search import SearchResponse
from appSunPQ.services.booking_service import BookingService
from appSunPQ.services.check_service import CheckService
from appSunPQ.services.confirm_price_service import ConfirmPriceService
from appSunPQ.services.hold_service import HoldService
from appSunPQ.services.minfare_service import MinFareService
from appSunPQ.services.search_service import SearchService
from appSunPQ.session_manager import SessionManager
from shared.logger import LogPrefix, get_logger

logger = get_logger(LogPrefix.GENERAL)


class SunPortalClient:
    """
    Facade chính để tương tác với Sun Portal API.

    Luồng chuẩn::

        client = SunPortalClient()

        # 1. Tìm kiếm
        search = client.search_simple(
            departure="ICN", arrival="HAN",
            depdate="2026-08-14", arrdate="2026-08-22",
            adt=1,
        )

        # 2. Xác nhận giá (create-booking)
        body    = search.formatted["body"][0]
        itin    = (body["chiều_đi"]["list_itinerary"]
                   + body["chiều_về"]["list_itinerary"])

        preview = client.create_booking_simple(
            list_itinerary=itin,
            list_passenger=[Passenger(pax_id=1, type="ADULT",
                                      first_name="XUAN SON", last_name="TRINH")],
            contact_info=ContactInfo(email="...", phone_number="+84...",
                                     full_name="Mr Son HVA"),
        )
        # preview.trace_id, preview.booking_status, preview.total_amount

        # 3. Giữ vé (hold-booking) — chỉ khi is_confirmed == True
        if preview.is_confirmed:
            hold = client.hold_simple(preview.trace_id)
            print(hold.pnr)
    """

    def __init__(
        self,
        state_file: str = STATE_FILE,
        headless: bool = True,
        auto_init: bool = True,
    ) -> None:
        self._session_manager = SessionManager(state_file=state_file, headless=headless)
        self._search_service  = SearchService(self._session_manager)
        self._hold_service    = HoldService(self._session_manager)
        self._booking_service = BookingService(self._session_manager)
        self._check_service   = CheckService(self._session_manager)
        self._minfare_service = MinFareService(self._session_manager)
        # NOTE: SearchService đã tự động gọi confirm-price bên trong
        # search()/search_simple() cho từng entry của formatted body — đây
        # là service riêng chỉ để dùng THỦ CÔNG (vd debug/test) nếu cần.
        self._confirm_price_service = ConfirmPriceService(self._session_manager)

        if auto_init:
            logger.info("Khởi tạo SunPortalClient...")
            self._session_manager.initialize()
            logger.info("SunPortalClient sẵn sàng.")

    # ── Search ───────────────────────────────────────────────────────────────

    def search(
        self,
        payload: dict[str, Any],
        override_url: str | None = None,
    ) -> SearchResponse:
        """Tìm kiếm với payload đầy đủ format Sun Portal."""
        return self._search_service.search(payload, override_url=override_url)

    def search_simple(
        self,
        departure: str,
        arrival: str,
        depdate: str,
        arrdate: str | None = None,
        trip_type: str = "RT",
        adt: int = 1,
        chd: int = 0,
        inf: int = 0,
        promo_code: str = "",
        currency: str = "KRW",
        override_url: str | None = None,
    ) -> SearchResponse:
        """
        Tìm kiếm với tham số ngắn gọn.

        Args:
            departure:  Sân bay đi ("ICN", "HAN", ...).
            arrival:    Sân bay đến.
            depdate:    Ngày đi "YYYY-MM-DD".
            arrdate:    Ngày về "YYYY-MM-DD" (bắt buộc nếu trip_type="RT").
            trip_type:  "RT" hoặc "OW".
            adt/chd/inf: Số lượng Adult / Child / Infant.
            promo_code: Mã khuyến mãi.
            currency:   "KRW", "VND", ...

        Example::

            search = client.search_simple(
                departure="ICN", arrival="HAN",
                depdate="2026-08-14", arrdate="2026-08-22",
                adt=1,
            )
        """
        list_route = [{"departure": departure, "arrival": arrival, "flight_date": depdate}]
        if trip_type == "RT":
            if not arrdate:
                raise ValueError("arrdate bắt buộc khi trip_type='RT'")
            list_route.append({"departure": arrival, "arrival": departure, "flight_date": arrdate})

        return self._search_service.search_simple(
            list_route=list_route,
            adult=adt, child=chd, infant=inf,
            trip_type=trip_type, currency=currency,
            promo_code=promo_code, override_url=override_url,
        )

    # ── Confirm Price (thủ công — search_simple đã tự gọi bước này rồi) ─────

    def confirm_price_simple(
        self,
        list_itinerary: list[dict[str, Any]],
        adult: int = 1,
        child: int = 0,
        infant: int = 0,
        trip_type: str = "RT",
        currency: str = "KRW",
        promo_code: str = "",
        corporate_code: str = "",
        override_url: str | None = None,
    ) -> ConfirmPriceResult:
        """
        Gọi thủ công POST /normal/create/confirm-price cho 1 tổ hợp
        itinerary cụ thể.

        LƯU Ý: ``search_simple()`` đã TỰ ĐỘNG gọi bước này cho từng entry
        trong ``formatted["body"]`` rồi (xem ``SearchService``) — hàm này
        chỉ hữu ích khi cần confirm lại thủ công (vd: sau khi khách chọn
        vé một lúc, muốn double-check giá trước khi tạo booking).

        Args:
            list_itinerary: PHẢI đúng format confirm-price (trip_id gốc
                dạng chuỗi, segment_id đánh số liên tục toàn bộ itinerary)
                — KHÔNG dùng ``formatted["body"][i]["chiều_đi"]["list_itinerary"]``
                (đó là format cho create-booking, khác nhau).
            adult/child/infant: Phải khớp với số hành khách lúc search.
            trip_type: "RT" hoặc "OW".
            currency: Mã tiền tệ.

        Returns:
            ConfirmPriceResult — ``result.total_amount`` là giá CHUẨN.
        """
        return self._confirm_price_service.confirm_price_simple(
            list_itinerary=list_itinerary,
            adult=adult, child=child, infant=infant,
            trip_type=trip_type, currency=currency,
            promo_code=promo_code, corporate_code=corporate_code,
            override_url=override_url,
        )

    # ── Create Booking (bước 1 — xác nhận giá) ───────────────────────────────

    def create_booking(
        self,
        payload: dict[str, Any],
        override_url: str | None = None,
    ) -> BookingPreviewResult:
        """
        Xác nhận giá với payload đầy đủ đã build sẵn.

        Returns:
            BookingPreviewResult — quan trọng nhất là ``trace_id``
            và ``is_confirmed`` để dùng cho hold tiếp theo.
        """
        return self._booking_service.create_booking(payload, override_url=override_url)

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
        Xác nhận giá với tham số ngắn gọn — tự build payload, tự suy ra trip_type.

        Args:
            list_itinerary:  Segment list ghép từ chiều đi + chiều về.
                             Lấy từ ``formatted["body"][i]["chiều_đi"]["list_itinerary"]``
                             + ``["chiều_về"]["list_itinerary"]`` (nếu RT).
            list_passenger:  list[Passenger] hoặc list[dict].
            contact_info:    ContactInfo hoặc dict.
            promo_code:      Mã khuyến mãi.
            corporate_code:  Mã hợp đồng.
            currency:        "KRW", "VND", ...

        Returns:
            BookingPreviewResult::

                preview.trace_id        # → dùng cho hold_simple()
                preview.booking_status  # "OK" = giá xác nhận
                preview.total_amount    # tổng tiền (KRW)
                preview.is_confirmed    # True nếu sẵn sàng hold

        Example::

            body    = search.formatted["body"][0]
            itin    = (body["chiều_đi"]["list_itinerary"]
                       + body["chiều_về"]["list_itinerary"])

            preview = client.create_booking_simple(
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
            print(preview.trace_id, preview.booking_status, preview.total_amount)
        """
        return self._booking_service.create_booking_simple(
            list_itinerary=list_itinerary,
            list_passenger=list_passenger,
            contact_info=contact_info,
            promo_code=promo_code,
            corporate_code=corporate_code,
            currency=currency,
            override_url=override_url,
        )

    # ── Hold Booking (bước 2 — giữ vé thật, lấy PNR) ────────────────────────

    def hold(
        self,
        payload: dict[str, Any],
        override_url: str | None = None,
    ) -> BookingResult:
        """
        Giữ vé với payload đầy đủ.

        Payload chuẩn::

            {"trace_id": "FLN...", "option": {"send_email": "Y"}}

        Dùng ``build_hold_payload(trace_id)`` từ ``appSunPQ.models.booking``
        để tạo payload, hoặc truyền thẳng dict.
        """
        return self._hold_service.hold(payload, override_url=override_url)

    def hold_simple(
        self,
        trace_id: str,
        send_email: bool = True,
        override_url: str | None = None,
    ) -> BookingResult:
        """
        Giữ vé từ trace_id — cách ngắn gọn nhất.

        Gọi ngay sau ``create_booking_simple`` khi ``preview.is_confirmed == True``.

        Args:
            trace_id:    Lấy từ ``BookingPreviewResult.trace_id``.
            send_email:  Gửi email xác nhận cho khách (mặc định True).

        Returns:
            BookingResult::

                hold.pnr              # mã PNR (FBF8CT)
                hold.expiration_date  # hạn thanh toán
                hold.total_amount     # tổng tiền phải trả
                hold.booking_status   # "OK" nếu giữ vé thành công
                hold.is_held          # True nếu success + có pnr + status OK

        Example::

            if preview.is_confirmed:
                hold = client.hold_simple(preview.trace_id)
                print(hold.pnr, hold.expiration_date, hold.total_amount)
        """
        return self._hold_service.hold_simple(
            trace_id=trace_id,
            send_email=send_email,
            override_url=override_url,
        )

    # ── Check Booking (tra cứu vé theo PNR) ─────────────────────────────────

    def check_booking(
        self,
        payload: dict[str, Any],
        override_url: str | None = None,
    ) -> CheckResult:
        """
        Tra cứu booking với payload đầy đủ.

        Payload chuẩn::

            {"pnr_number": "FBX5UK"}
        """
        return self._check_service.check_booking(payload, override_url=override_url)

    def check_booking_simple(
        self,
        pnr: str,
        override_url: str | None = None,
    ) -> CheckResult:
        """
        Tra cứu booking từ mã PNR — cách ngắn gọn nhất.

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
                result.hanthanhtoan    # hạn thanh toán
                result.chieudi         # list segment chiều đi
                result.chieuve         # list segment chiều về
                result.passengers      # list hành khách

        Example::

            result = client.check_booking_simple("FBX5UK")
            print(result.to_dict())
        """
        return self._check_service.check_booking_simple(
            pnr=pnr,
            override_url=override_url,
        )

    # ── Min-Fare (giá rẻ theo ngày) ──────────────────────────────────────────

    def search_minfare_simple(
        self,
        departure: str,
        arrival: str,
        flight_date: str,
        adult: int = 1,
        child: int = 0,
        infant: int = 0,
        day_interval: int = 7,
        currency: str = "KRW",
        override_url: str | None = None,
    ) -> MinFareResult:
        """
        Tra giá thấp nhất ±day_interval ngày quanh flight_date (1 chiều).

        RT cần gọi 2 lần riêng: 1 cho chiều đi, 1 cho chiều về.

        Returns:
            MinFareResult — dùng ``.to_list()`` để lấy
            ``[{"ngày": "07/08/2026", "giá_vé_gốc": 316800}, ...]``.
        """
        return self._minfare_service.search_minfare(
            departure=departure,
            arrival=arrival,
            flight_date=flight_date,
            adult=adult,
            child=child,
            infant=infant,
            day_interval=day_interval,
            currency=currency,
            override_url=override_url,
        )

    # ── Utilities ────────────────────────────────────────────────────────────

    def force_relogin(self) -> None:
        """Buộc đăng nhập lại bằng Playwright."""
        logger.info("Force relogin được yêu cầu...")
        self._session_manager._login_with_playwright()
        logger.info("Relogin hoàn tất.")

    def check_session(self) -> bool:
        """Kiểm tra session có còn hợp lệ không."""
        return self._session_manager._is_session_valid()
