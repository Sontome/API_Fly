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
