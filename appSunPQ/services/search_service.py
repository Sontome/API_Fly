"""
appSunPQ/services/search_service.py
Service tìm kiếm chuyến bay Sun Portal.

Endpoint: POST /normal/search

Payload thật (ví dụ khứ hồi ICN <-> HAN)::

    {
        "adult": 1,
        "child": 0,
        "infant": 0,
        "list_route": [
            {"departure": "ICN", "arrival": "HAN", "flight_date": "2026-06-20"},
            {"departure": "HAN", "arrival": "ICN", "flight_date": "2026-06-21"}
        ],
        "option": {
            "direct_only": false,
            "promo_code": "",
            "corporate_code": "",
            "trip_type": "RT",
            "point_of_purchase": "",
            "currency": "KRW",
            "fare_family": ["9GECO", "9GBUZ"]
        }
    }
"""

from __future__ import annotations

from typing import Any

from appSunPQ.constants import DEFAULT_CURRENCY, DEFAULT_FARE_FAMILY
from appSunPQ.endpoints import SEARCH_FLIGHT
from appSunPQ.models.search import SearchResponse
from appSunPQ.services.confirm_price_service import ConfirmPriceService
from appSunPQ.session_manager import SessionManager
from shared.exceptions import SearchError
from shared.logger import LogPrefix, get_logger

logger = get_logger(LogPrefix.SEARCH)


class Route(dict):
    """
    Đại diện cho 1 chặng tìm kiếm (route) trong list_route.

    Có thể dùng trực tiếp dict hoặc khởi tạo qua Route(...) cho rõ nghĩa::

        Route(departure="ICN", arrival="HAN", flight_date="2026-06-20")
    """

    def __init__(self, departure: str, arrival: str, flight_date: str) -> None:
        super().__init__(departure=departure, arrival=arrival, flight_date=flight_date)


class SearchService:
    """
    Tìm kiếm chuyến bay qua Sun Portal API.

    Endpoint: POST /normal/search
    """

    def __init__(self, session_manager: SessionManager) -> None:
        self._sm = session_manager
        self._confirm_service = ConfirmPriceService(session_manager)

    # ── Public API ──────────────────────────────────────────────────────

    def search(
        self,
        payload: dict[str, Any],
        override_url: str | None = None,
    ) -> SearchResponse:
        """
        Tìm kiếm chuyến bay với payload đúng format Sun Portal (raw).

        Args:
            payload: Payload đầy đủ theo format Sun Portal (adult, child,
                infant, list_route, option).
            override_url: Ghi đè URL endpoint (dùng khi test/staging).

        Returns:
            SearchResponse chứa list_flight (trip_map) + recommendation.

        Raises:
            SearchError: Nếu request thất bại hoặc response success=False.

        Example::

            payload = {
                "adult": 1,
                "child": 0,
                "infant": 0,
                "list_route": [
                    {"departure": "ICN", "arrival": "HAN", "flight_date": "2026-06-20"},
                    {"departure": "HAN", "arrival": "ICN", "flight_date": "2026-06-21"},
                ],
                "option": {
                    "direct_only": False,
                    "promo_code": "555555",
                    "corporate_code": "",
                    "trip_type": "RT",
                    "point_of_purchase": "",
                    "currency": "KRW",
                    "fare_family": ["9GECO", "9GBUZ"],
                },
            }
            result = service.search(payload)
        """
        url = override_url or SEARCH_FLIGHT
        http = self._sm.get_http_client()
        headers = self._sm.get_headers()

        routes = payload.get("list_route", [])
        route_desc = " | ".join(
            f"{r.get('departure')}->{r.get('arrival')} ({r.get('flight_date')})"
            for r in routes
        )
        logger.info(f"Tìm kiếm: {route_desc or '(không có route)'}")
        logger.debug(f"POST {url} payload={payload}")

        try:
            response = http.post(url, headers=headers, json=payload)
            data = response.json()
            result = SearchResponse.from_dict(data)

            if not result.success:
                raise SearchError(
                    f"Search trả về success=False: {result.error}",
                    code="SEARCH_FAILED",
                )

            logger.info(
                f"Kết quả tìm kiếm: {result.total_count} recommendation, "
                f"{len(result.trip_map)} trip, success={result.success}"
            )

            # ── Confirm lại giá chuẩn cho từng "vé" trong formatted body ──
            # Giá trong recommendation là giá GỢI Ý — cần confirm-price cho
            # đúng tổ hợp itinerary đã ghép (mỗi entry = 1 lần gọi, gồm cả
            # chiều đi + chiều về nếu khứ hồi) để lấy giá chuẩn cuối cùng.
            # Entry nào confirm lỗi/không hợp lệ sẽ bị loại khỏi kết quả.
            self._confirm_and_filter_body(result, payload)

            return result

        except SearchError:
            raise
        except Exception as e:
            logger.exception(f"Tìm kiếm thất bại: {e}")
            raise SearchError(f"Search thất bại: {e}") from e

    def search_simple(
        self,
        list_route: list[dict[str, str]],
        adult: int = 1,
        child: int = 0,
        infant: int = 0,
        trip_type: str = "RT",
        currency: str = DEFAULT_CURRENCY,
        fare_family: list[str] | None = None,
        direct_only: bool = False,
        promo_code: str = "",
        corporate_code: str = "",
        point_of_purchase: str = "",
        override_url: str | None = None,
    ) -> SearchResponse:
        """
        Helper build payload từ tham số rời rồi gọi search().

        Args:
            list_route: Danh sách route, mỗi route là dict
                {"departure": "ICN", "arrival": "HAN", "flight_date": "2026-06-20"}.
                Khứ hồi (RT) cần 2 route (đi + về), một chiều (OW) cần 1 route.
            adult/child/infant: Số lượng hành khách từng loại.
            trip_type: "RT" (round-trip) hoặc "OW" (one-way).
            currency: Mã tiền tệ hiển thị giá (ví dụ "KRW", "VND").
            fare_family: Danh sách fare family cần tìm
                (mặc định ["9GECO", "9GBUZ"]).
            direct_only: Chỉ tìm chuyến bay thẳng (không nối chuyến).
            promo_code: Mã khuyến mãi (nếu có).
            corporate_code: Mã hợp đồng công ty (nếu có).
            point_of_purchase: Điểm bán (nếu có).
            override_url: Ghi đè URL endpoint.

        Returns:
            SearchResponse.

        Example::

            result = service.search_simple(
                list_route=[
                    {"departure": "ICN", "arrival": "HAN", "flight_date": "2026-06-20"},
                    {"departure": "HAN", "arrival": "ICN", "flight_date": "2026-06-21"},
                ],
                adult=1,
                currency="KRW",
            )

            cheapest = result.cheapest()
            print(cheapest.total_amount, cheapest.currency)
            for itinerary in cheapest.itineraries:
                for trip in itinerary.trips:
                    print(trip.trip_id, trip.route, trip.elapse_flying_time)
        """
        payload: dict[str, Any] = {
            "adult": adult,
            "child": child,
            "infant": infant,
            "list_route": list_route,
            "option": {
                "direct_only": direct_only,
                "promo_code": promo_code,
                "corporate_code": corporate_code,
                "trip_type": trip_type,
                "point_of_purchase": point_of_purchase,
                "currency": currency,
                "fare_family": fare_family or list(DEFAULT_FARE_FAMILY),
            },
        }
        return self.search(payload, override_url=override_url)

    # ── Internal: confirm-price cho formatted body ─────────────────────────

    def _confirm_and_filter_body(
        self,
        result: SearchResponse,
        payload: dict[str, Any],
    ) -> None:
        """
        Với mỗi entry trong ``result.formatted["body"]``, gọi
        POST /normal/create/confirm-price (1 lần/entry, gồm cả chiều đi +
        chiều về nếu khứ hồi — xem ``ConfirmPriceService``) để lấy giá
        CHUẨN, rồi cập nhật lại ``thông_tin_chung.giá_vé`` bằng tổng tiền
        đã confirm.

        Quy ước:
        - Giá TỪNG CHIỀU (``chiều_đi.giá_vé_gốc`` / ``chiều_về.giá_vé_gốc``)
          GIỮ NGUYÊN như giá ước tính từ search (confirm-price chỉ trả về
          MỘT tổng duy nhất cho khứ hồi, không tách được theo từng chiều).
        - Nếu confirm-price lỗi / trả về không hợp lệ (success=False hoặc
          total_amount <= 0) cho 1 entry → BỎ HẲN entry đó khỏi kết quả trả
          về (không hiển thị giá chưa chắc chắn cho khách).
        - Field nội bộ ``_confirm_itinerary`` luôn bị xóa khỏi entry trước
          khi trả về (không phải dữ liệu client cần thấy).

        Mutates ``result.formatted["body"]`` in-place (thay bằng danh sách
        đã lọc + cập nhật giá).
        """
        adult = payload.get("adult", 1)
        child = payload.get("child", 0)
        infant = payload.get("infant", 0)
        option = payload.get("option") or {}
        trip_type = option.get("trip_type", "RT")
        currency = option.get("currency", DEFAULT_CURRENCY)
        promo_code = option.get("promo_code", "")
        corporate_code = option.get("corporate_code", "")

        body = result.formatted.get("body", [])
        confirmed_body: list[dict[str, Any]] = []

        for entry in body:
            confirm_itinerary = entry.pop("_confirm_itinerary", None)

            if not confirm_itinerary:
                logger.warning(
                    "Bỏ 1 entry khỏi kết quả: thiếu dữ liệu để confirm-price"
                )
                continue

            try:
                confirmed = self._confirm_service.confirm_price_simple(
                    list_itinerary=confirm_itinerary,
                    adult=adult, child=child, infant=infant,
                    trip_type=trip_type, currency=currency,
                    promo_code=promo_code, corporate_code=corporate_code,
                )
            except Exception as e:
                logger.warning(
                    f"Confirm-price thất bại cho 1 entry, bỏ khỏi kết quả: {e}"
                )
                continue

            if not confirmed.is_valid:
                logger.warning(
                    "Confirm-price trả về không hợp lệ (success=False hoặc "
                    "total_amount<=0), bỏ entry khỏi kết quả"
                )
                continue

            summary = dict(entry.get("thông_tin_chung") or {})
            summary["giá_vé"] = str(int(confirmed.total_amount))
            entry["thông_tin_chung"] = summary

            confirmed_body.append(entry)

        logger.info(
            f"Confirm-price: {len(confirmed_body)}/{len(body)} entry hợp lệ "
            "sau khi xác nhận giá"
        )
        result.formatted["body"] = confirmed_body
