"""
appSunPQ/services/minfare_service.py
Service tra giá thấp nhất theo ngày (search-minfare).

Endpoint: POST /normal/search-minfare

Dùng cho endpoint /spa/check-ve-v3:
  - OW: gọi 1 lần với route chiều đi
  - RT: gọi 2 lần riêng biệt (chiều đi, chiều về), mỗi lần trip_type=OW
"""

from __future__ import annotations

from typing import Any

from appSunPQ.endpoints import SEARCH_MINFARE
from appSunPQ.models.minfare import MinFareResult
from appSunPQ.session_manager import SessionManager
from shared.logger import LogPrefix, get_logger

logger = get_logger(LogPrefix.SEARCH)


class MinFareService:
    """
    Tra giá thấp nhất theo ngày qua POST /normal/search-minfare.

    RT phải gọi 2 lần riêng biệt (server chỉ nhận OW cho minfare).
    """

    def __init__(self, session_manager: SessionManager) -> None:
        self._sm = session_manager

    def search_minfare(
        self,
        departure: str,
        arrival: str,
        flight_date: str,
        adult: int = 1,
        child: int = 0,
        infant: int = 0,
        day_interval: int = 7,
        currency: str = "KRW",
        promo_code: str = "",
        override_url: str | None = None,
    ) -> MinFareResult:
        """
        Tìm giá thấp nhất ±day_interval ngày quanh flight_date cho 1 chiều.

        Args:
            departure:    Mã IATA sân bay đi.
            arrival:      Mã IATA sân bay đến.
            flight_date:  Ngày bay "YYYY-MM-DD" (trung tâm của khung tìm kiếm).
            adult:        Số người lớn.
            child:        Số trẻ em.
            infant:       Số trẻ sơ sinh.
            day_interval: Số ngày trước/sau flight_date để tìm (mặc định 7).
            currency:     Tiền tệ.
            promo_code:   Mã khuyến mãi.
            override_url: Ghi đè URL.

        Returns:
            MinFareResult với list DayFare đã sort theo ngày.
        """
        payload = self._build_payload(
            departure=departure,
            arrival=arrival,
            flight_date=flight_date,
            adult=adult,
            child=child,
            infant=infant,
            day_interval=day_interval,
            currency=currency,
            promo_code=promo_code,
        )
        return self._post(payload, override_url)

    # ── Internal ────────────────────────────────────────────────────────────

    def _build_payload(
        self,
        departure: str,
        arrival: str,
        flight_date: str,
        adult: int,
        child: int,
        infant: int,
        day_interval: int,
        currency: str,
        promo_code: str,
    ) -> dict[str, Any]:
        return {
            "adult": adult,
            "child": child,
            "infant": infant,
            "list_route": [
                {
                    "departure": departure,
                    "arrival": arrival,
                    "flight_date": flight_date,
                }
            ],
            "option": {
                "direct_only": False,
                "promo_code": promo_code,
                "corporate_code": "",
                "trip_type": "OW",           # minfare luôn OW
                "point_of_purchase": "",
                "day_interval": day_interval,
                "currency": currency,
                "fare_family": ["9GECO"],
            },
        }

    def _post(
        self,
        payload: dict[str, Any],
        override_url: str | None,
    ) -> MinFareResult:
        url = override_url or SEARCH_MINFARE
        http = self._sm.get_http_client()
        headers = self._sm.get_headers()

        dep = payload["list_route"][0]["departure"]
        arr = payload["list_route"][0]["arrival"]
        date = payload["list_route"][0]["flight_date"]
        logger.info(f"Search minfare: {dep}→{arr} quanh {date}")

        try:
            response = http.post(url, headers=headers, json=payload)
            data = response.json()
            result = MinFareResult.from_dict(data)
            logger.info(f"Minfare result: {len(result.days)} ngày có giá")
            return result
        except Exception as e:
            logger.exception(f"Search minfare thất bại: {e}")
            # Trả về kết quả rỗng thay vì raise — lỗi minfare không chặn
            # việc check booking chính
            return MinFareResult()
