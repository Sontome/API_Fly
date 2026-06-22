"""
appSunPQ/models/minfare.py
Model cho Search Min-Fare API (POST /normal/search-minfare).

Response trả về giá rẻ nhất theo từng ngày (±7 ngày quanh ngày tìm kiếm).
Mục đích: hiển thị "giá vé thấp nhất theo ngày" cho user chọn ngày linh hoạt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DayFare:
    """Giá rẻ nhất trong một ngày cụ thể."""
    ngay: str           # "07/08/2026"  (DD/MM/YYYY)
    gia_ve_goc: float   # giá ADULT total_amount

    def to_dict(self) -> dict[str, Any]:
        return {"ngày": self.ngay, "giá_vé_gốc": self.gia_ve_goc}


@dataclass
class MinFareResult:
    """
    Kết quả parse từ POST /normal/search-minfare.

    Response thật::

        {
            "data": {
                "list_flight": [
                    {
                        "departure": "ICN", "arrival": "HAN",
                        "list_trip": [
                            {
                                "trip_id": "ICNHAN-7",
                                "stop_number": 1,
                                "list_itinerary": [
                                    {
                                        "segment_id": 1,
                                        "flight_date": "2026-08-07",
                                        "carrier": "9G", "flight_number": 455,
                                        "departure_info": {"code": "ICN", ...},
                                        "arrival_info": {"code": "PQC", ...}
                                    },
                                    ...
                                ]
                            }, ...
                        ]
                    }
                ],
                "recommendation": [
                    {
                        "list_segment": [{"list_trip": ["ICNHAN-1"]}, ...],
                        "list_pax_pricing": [
                            {
                                "type": "ADULT",
                                "fare": {"currency": "KRW", "total_amount": 273400, ...}
                            }
                        ]
                    }, ...
                ]
            },
            "success": true, "trace_id": "FLN..."
        }

    Logic join:
    - Mỗi ``recommendation`` có ``list_segment[].list_trip[]`` = danh sách trip_id.
    - Tra cứu trip_id trong ``list_flight[0].list_trip`` để lấy ``flight_date``
      của segment đầu (đây là ngày khởi hành thật).
    - Giá lấy từ ``list_pax_pricing`` loại ADULT (``fare.total_amount``).
    - Mỗi trip_id trong recommendation → 1 entry {ngày, giá_vé_gốc}.
    - Sắp xếp kết quả theo ngày tăng dần.
    """
    days: list[DayFare] = field(default_factory=list)
    trace_id: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    def to_list(self) -> list[dict[str, Any]]:
        """Trả về list[{"ngày": ..., "giá_vé_gốc": ...}] đã sort theo ngày."""
        return [d.to_dict() for d in self.days]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MinFareResult":
        """
        Parse từ response thật của POST /normal/search-minfare.

        Args:
            data: Toàn bộ response JSON (bao gồm cả wrapper success/trace_id).
        """
        if not data.get("success"):
            return cls(raw=data)

        inner = data.get("data") or {}
        trace_id = data.get("trace_id", "")

        # ── Bước 1: Build map trip_id → flight_date (ngày của segment đầu) ──
        # list_flight thường chỉ có 1 phần tử (1 route), nhưng duyệt hết
        # để đảm bảo không bỏ sót.
        trip_date_map: dict[str, str] = {}  # trip_id → "YYYY-MM-DD"
        for flight in inner.get("list_flight", []):
            for trip in flight.get("list_trip", []):
                tid = trip.get("trip_id", "")
                itineraries = trip.get("list_itinerary", [])
                if itineraries:
                    # Lấy flight_date từ segment đầu tiên (segment_id nhỏ nhất)
                    first_itin = min(
                        itineraries,
                        key=lambda x: x.get("segment_id", 0),
                    )
                    trip_date_map[tid] = first_itin.get("flight_date", "")

        # ── Bước 2: Join recommendation → DayFare ───────────────────────────
        # Mỗi recommendation có 1 mức giá + nhiều trip_id.
        # Mỗi trip_id trong recommendation → 1 entry riêng (1 ngày riêng).
        day_map: dict[str, float] = {}  # "YYYY-MM-DD" → giá (ADULT total_amount)

        for rec in inner.get("recommendation", []):
            # Lấy giá ADULT (ưu tiên ADULT, fallback bất kỳ loại đầu tiên)
            pax_pricings = rec.get("list_pax_pricing", [])
            price = 0.0
            for pp in pax_pricings:
                if pp.get("type") == "ADULT":
                    price = float(pp.get("fare", {}).get("total_amount", 0))
                    break
            if price == 0.0 and pax_pricings:
                price = float(pax_pricings[0].get("fare", {}).get("total_amount", 0))

            # Duyệt tất cả trip_id trong recommendation này
            for seg in rec.get("list_segment", []):
                for tid in seg.get("list_trip", []):
                    flight_date = trip_date_map.get(tid, "")
                    if flight_date:
                        # Nếu ngày đã tồn tại, giữ giá thấp hơn
                        if flight_date not in day_map or price < day_map[flight_date]:
                            day_map[flight_date] = price

        # ── Bước 3: Chuyển "YYYY-MM-DD" → "DD/MM/YYYY" và sort ─────────────
        days: list[DayFare] = []
        for iso_date in sorted(day_map):          # sort theo YYYY-MM-DD OK
            try:
                parts = iso_date.split("-")
                display = f"{parts[2]}/{parts[1]}/{parts[0]}"
            except IndexError:
                display = iso_date
            days.append(DayFare(ngay=display, gia_ve_goc=day_map[iso_date]))

        return cls(days=days, trace_id=trace_id, raw=data)
