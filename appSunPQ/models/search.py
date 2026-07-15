"""
appSunPQ/models/search.py
Models cho Search API (POST /normal/search).
 
Cấu trúc response thật của Sun Portal::
 
    {
        "data": {
            "list_flight": [
                {
                    "departure": "ICN",
                    "arrival": "HAN",
                    "route": "ICN-HAN",
                    "list_trip": [
                        {
                            "trip_id": "ICNHAN-1",
                            "stop_number": 1,
                            "elapse_flying_time": "1255",
                            "list_itinerary": [ {...segment...}, ... ]
                        },
                        ...
                    ]
                },
                ...
            ],
            "recommendation": [
                {
                    "list_segment": [
                        {"list_trip": ["ICNHAN-1", "HANICN-1"]},
                        ...
                    ],
                    "list_pax_pricing": [
                        {
                            "type": "ADULT",
                            "list_fare": [
                                {"route": "ICNHAN", "total_amount": ..., ...},
                                {"route": "HANICN", "total_amount": ..., ...}
                            ]
                        }
                    ]
                },
                ...
            ]
        },
        "error": null,
        "success": true,
        "trace_id": "..."
    }
 
Một "recommendation" có thể chứa nhiều "list_segment" (nhiều tổ hợp
trip_id khác nhau) nhưng dùng CHUNG một bộ giá (list_pax_pricing) —
vì các trip trong cùng route thường cùng hạng vé / fare_basis.
"""
 
from __future__ import annotations
 
from dataclasses import dataclass, field
from typing import Any


# ─────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────

# Các mã sân bay được coi là "xuất phát từ Hàn Quốc". Mở rộng thêm nếu cần.
KOREA_AIRPORT_CODES: set[str] = {
    "ICN", "GMP", "PUS", "CJU", "TAE", "KWJ", "USN", "CJJ",
}

# Nhóm hạng vé "đặc biệt" (promo) — dùng để phân loại recommendation khi
# điểm khởi hành là Hàn Quốc.
PREMIUM_BOOKING_CLASSES: set[str] = {"S", "G", "A", "X"}
 
 
# ─────────────────────────────────────────────────────────────────────────
# Flight / Trip / Segment (list_flight)
# ─────────────────────────────────────────────────────────────────────────
 
@dataclass
class AirportPoint:
    """Thông tin điểm đi/đến của một chặng bay."""
    code: str = ""
    datetime: str = ""
    terminal: str = ""
 
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AirportPoint":
        return cls(
            code=data.get("code", ""),
            datetime=data.get("datetime", ""),
            terminal=data.get("terminal", ""),
        )
 
 
@dataclass
class FlightSegment:
    """Một chặng bay cụ thể (segment) trong một trip."""
    segment_id: int = 0
    flight_date: str = ""
    carrier: str = ""
    flight_number: int | str = ""
    duration: str = ""  # dạng "HHMM", ví dụ "0540" = 5h40
    aircraft_type: str = ""
    departure: AirportPoint = field(default_factory=AirportPoint)
    arrival: AirportPoint = field(default_factory=AirportPoint)
    raw: dict[str, Any] = field(default_factory=dict)
 
    @property
    def flight_code(self) -> str:
        """Mã chuyến bay đầy đủ, ví dụ '9G451'."""
        return f"{self.carrier}{self.flight_number}"
 
    @property
    def duration_minutes(self) -> int:
        """Thời gian bay (phút), parse từ chuỗi 'HHMM'."""
        return _hhmm_to_minutes(self.duration)
 
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FlightSegment":
        return cls(
            segment_id=data.get("segment_id", 0),
            flight_date=data.get("flight_date", ""),
            carrier=data.get("carrier", ""),
            flight_number=data.get("flight_number", ""),
            duration=data.get("duration", ""),
            aircraft_type=data.get("aircraft_info", {}).get("type", ""),
            departure=AirportPoint.from_dict(data.get("departure_info", {})),
            arrival=AirportPoint.from_dict(data.get("arrival_info", {})),
            raw=data,
        )
 
 
@dataclass
class Trip:
    """
    Một "trip" = một lựa chọn hành trình cho 1 route (có thể nhiều chặng nối).
    Tương ứng với trip_id (ví dụ "ICNHAN-1").
    """
    trip_id: str = ""
    route: str = ""
    departure: str = ""
    arrival: str = ""
    stop_number: int = 0
    elapse_flying_time: str = ""  # tổng thời gian "HHMM" (bao gồm cả thời gian nối chuyến)
    segments: list[FlightSegment] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
 
    @property
    def elapse_flying_minutes(self) -> int:
        return _hhmm_to_minutes(self.elapse_flying_time)
 
    @property
    def departure_datetime(self) -> str:
        """Thời gian khởi hành của chặng đầu tiên."""
        return self.segments[0].departure.datetime if self.segments else ""
 
    @property
    def arrival_datetime(self) -> str:
        """Thời gian đến của chặng cuối cùng."""
        return self.segments[-1].arrival.datetime if self.segments else ""
 
    @classmethod
    def from_dict(cls, data: dict[str, Any], route: str, departure: str, arrival: str) -> "Trip":
        segments = [
            FlightSegment.from_dict(seg)
            for seg in data.get("list_itinerary", [])
        ]
        return cls(
            trip_id=data.get("trip_id", ""),
            route=route,
            departure=departure,
            arrival=arrival,
            stop_number=data.get("stop_number", 0),
            elapse_flying_time=data.get("elapse_flying_time", ""),
            segments=segments,
            raw=data,
        )
 
 
# ─────────────────────────────────────────────────────────────────────────
# Pricing (recommendation.list_pax_pricing)
# ─────────────────────────────────────────────────────────────────────────
 
@dataclass
class SegmentFareInfo:
    """Thông tin hạng đặt chỗ cho 1 segment trong route fare."""
    fare_basis: str = ""
    booking_class: str = ""
    seat_availability: int = 0
    break_point: str = ""
 
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SegmentFareInfo":
        return cls(
            fare_basis=data.get("fare_basis", ""),
            booking_class=data.get("booking_class", ""),
            seat_availability=data.get("seat_availability", 0),
            break_point=data.get("break_point", ""),
        )
 
 
@dataclass
class RouteFare:
    """Giá vé cho 1 route (ví dụ 'ICNHAN' hoặc 'HANICN')."""
    route: str = ""
    booking_class: str = ""
    currency: str = "KRW"
    display_fare: float = 0.0
    applied_fare: float = 0.0
    base_fare: float = 0.0
    tax: float = 0.0
    total_amount: float = 0.0
    baggage_weight: int = 0
    segment_fare: list[SegmentFareInfo] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
 
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RouteFare":
        return cls(
            route=data.get("route", ""),
            booking_class=data.get("booking_class", ""),
            currency=data.get("currency", "KRW"),
            display_fare=float(data.get("display_fare", 0)),
            applied_fare=float(data.get("applied_fare", 0)),
            base_fare=float(data.get("base_fare", 0)),
            tax=float(data.get("tax", 0)),
            total_amount=float(data.get("total_amount", 0)),
            baggage_weight=data.get("baggage_allowance", {}).get("weight", 0),
            segment_fare=[
                SegmentFareInfo.from_dict(sf) for sf in data.get("segment_fare", [])
            ],
            raw=data,
        )
 
 
@dataclass
class PaxPricing:
    """Giá vé theo loại khách (ADULT / CHILD / INFANT)."""
    type: str = ""
    list_fare: list[RouteFare] = field(default_factory=list)
 
    @property
    def total_amount(self) -> float:
        """Tổng tiền (tất cả route) cho loại khách này."""
        return sum(f.total_amount for f in self.list_fare)
 
    @property
    def currency(self) -> str:
        return self.list_fare[0].currency if self.list_fare else "KRW"
 
    def fare_for_route(self, route: str) -> RouteFare | None:
        """Lấy RouteFare theo mã route (ví dụ 'ICNHAN')."""
        for f in self.list_fare:
            if f.route == route:
                return f
        return None
 
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PaxPricing":
        return cls(
            type=data.get("type", ""),
            list_fare=[RouteFare.from_dict(f) for f in data.get("list_fare", [])],
        )
 
 
# ─────────────────────────────────────────────────────────────────────────
# Recommendation
# ─────────────────────────────────────────────────────────────────────────
 
@dataclass
class Itinerary:
    """Một tổ hợp hành trình cụ thể = list trip_id cho từng route."""
    trip_ids: list[str] = field(default_factory=list)
    trips: list[Trip] = field(default_factory=list)
 
    @classmethod
    def from_dict(cls, data: dict[str, Any], trip_map: dict[str, Trip]) -> "Itinerary":
        trip_ids = data.get("list_trip", [])
        trips = [trip_map[tid] for tid in trip_ids if tid in trip_map]
        return cls(trip_ids=trip_ids, trips=trips)
 
 
@dataclass
class Recommendation:
    """
    Một gói gợi ý kết quả tìm kiếm: gồm một hoặc nhiều tổ hợp hành trình
    (itinerary) cùng dùng chung một bộ giá (list_pax_pricing).
    """
    itineraries: list[Itinerary] = field(default_factory=list)
    pax_pricing: list[PaxPricing] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
 
    @property
    def adult_pricing(self) -> PaxPricing | None:
        for p in self.pax_pricing:
            if p.type == "ADULT":
                return p
        return self.pax_pricing[0] if self.pax_pricing else None
 
    @property
    def total_amount(self) -> float:
        """Tổng tiền (theo ADULT) cho cả round-trip / tổ hợp."""
        pricing = self.adult_pricing
        return pricing.total_amount if pricing else 0.0
 
    @property
    def currency(self) -> str:
        pricing = self.adult_pricing
        return pricing.currency if pricing else "KRW"
 
    @classmethod
    def from_dict(cls, data: dict[str, Any], trip_map: dict[str, Trip]) -> "Recommendation":
        itineraries = [
            Itinerary.from_dict(seg, trip_map) for seg in data.get("list_segment", [])
        ]
        pax_pricing = [
            PaxPricing.from_dict(p) for p in data.get("list_pax_pricing", [])
        ]
        return cls(itineraries=itineraries, pax_pricing=pax_pricing, raw=data)
 
 
# ─────────────────────────────────────────────────────────────────────────
# Top-level response
# ─────────────────────────────────────────────────────────────────────────
 
@dataclass
class SearchResponse:
    """Response đầy đủ từ POST /normal/search."""
    success: bool = False
    error: Any = None
    trace_id: str = ""
    trip_map: dict[str, Trip] = field(default_factory=dict)
    recommendations: list[Recommendation] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
    formatted: dict[str, Any] = field(default_factory=dict)
    # ── Helpers ──────────────────────────────────────────────────────────
 
    @property
    def total_count(self) -> int:
        """Tổng số gói gợi ý (recommendation)."""
        return len(self.recommendations)
 
    def get_trip(self, trip_id: str) -> Trip | None:
        """Lấy Trip theo trip_id."""
        return self.trip_map.get(trip_id)
 
    def trips_for_route(self, route: str) -> list[Trip]:
        """
        Lấy danh sách trip cho 1 route (ví dụ 'ICN-HAN' hoặc 'ICNHAN').
 
        Args:
            route: Route dạng "ICN-HAN" (trong list_flight) hoặc
                   "ICNHAN" (trong list_pax_pricing) — đều được chấp nhận.
        """
        normalized = route.replace("-", "")
        return [
            t for t in self.trip_map.values()
            if t.route.replace("-", "") == normalized
        ]
 
    def cheapest(self) -> Recommendation | None:
        """Lấy recommendation rẻ nhất (theo tổng tiền ADULT)."""
        if not self.recommendations:
            return None
        return min(self.recommendations, key=lambda r: r.total_amount)
 
    def sorted_by_price(self, reverse: bool = False) -> list[Recommendation]:
        """Sắp xếp toàn bộ recommendation theo giá."""
        return sorted(self.recommendations, key=lambda r: r.total_amount, reverse=reverse)
 
    # ── Parsing ──────────────────────────────────────────────────────────
 
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SearchResponse":
        """
        Parse từ dict API response (toàn bộ JSON trả về).
 
        Trả về thêm ``formatted`` chứa::
 
            {
                "trace_id": "...",
                "body": [
                    {
                        "chiều_đi":   { ... },
                        "chiều_về":   { ... },
                        "thông_tin_chung": { ... }
                    },
                    ...
                ]
            }
 
        ``body`` được build từ ``recommendation[0].list_segment`` (danh sách
        các cặp trip rẻ nhất đã ghép sẵn bởi server), mỗi phần tử là một
        cặp (chiều đi, chiều về). Giá lấy từ ``recommendation[0].list_pax_pricing``.
        """
        success = bool(data.get("success", False))
        error = data.get("error")
        trace_id = data.get("trace_id", "")
        inner = data.get("data") or {}
 
        # ── 1. Build trip_map: trip_id -> Trip ──────────────────────────────
        trip_map: dict[str, Trip] = {}
        for flight_group in inner.get("list_flight", []):
            route = flight_group.get("route", "")
            departure = flight_group.get("departure", "")
            arrival = flight_group.get("arrival", "")
            for trip_data in flight_group.get("list_trip", []):
                trip = Trip.from_dict(trip_data, route=route, departure=departure, arrival=arrival)
                trip_map[trip.trip_id] = trip
 
        # ── 2. Build recommendations ─────────────────────────────────────────
        recommendations = [
            Recommendation.from_dict(rec, trip_map)
            for rec in inner.get("recommendation", [])
        ]
 
        # ── 3. Build formatted body ──────────────────────────────────────────
        # Xác định điểm khởi hành (departure của route/chặng đầu tiên trong
        # list_flight) để biết có phải xuất phát từ Hàn Quốc hay không.
        departure_code = ""
        list_flight = inner.get("list_flight", [])
        if list_flight:
            departure_code = list_flight[0].get("departure", "")

        body: list[dict[str, Any]] = []

        if recommendations:
            if departure_code in KOREA_AIRPORT_CODES:
                # ── Xuất phát từ Hàn Quốc ────────────────────────────────
                # Cần trả về TOÀN BỘ vé của TẤT CẢ recommendation thỏa mãn
                # (không dừng lại ở recommendation đầu tiên tìm thấy):
                #   (1) các recommendation có hạng đi (và hạng về, nếu là
                #       khứ hồi) đều thuộc nhóm PREMIUM_BOOKING_CLASSES
                #       (S, G, A, X)
                #   (2) các recommendation có hạng đi VÀ hạng về đều KHÔNG
                #       thuộc nhóm đó
                # Nếu một recommendation có 2 chiều lệch nhóm (1 bên premium,
                # 1 bên không) thì recommendation đó không thỏa mãn cho cả
                # 2 trường hợp trên → bỏ qua.
                recs_premium = _find_recommendations_by_class_group(
                    recommendations, want_premium=True
                )
                recs_normal = _find_recommendations_by_class_group(
                    recommendations, want_premium=False
                )

                for rec in [*recs_premium, *recs_normal]:
                    body.extend(_build_entries_from_recommendation(rec))

                # Fallback: không tìm thấy recommendation nào thỏa điều kiện
                # → giữ hành vi cũ (dùng recommendation[0]) để tránh body rỗng.
                if not body:
                    body.extend(_build_entries_from_recommendation(recommendations[0]))
            else:
                # ── Điểm khởi hành khác Hàn Quốc: giữ nguyên logic cũ ───
                # (luôn lấy recommendation[0])
                body.extend(_build_entries_from_recommendation(recommendations[0]))
 
        obj = cls(
            success=success,
            error=error,
            trace_id=trace_id,
            trip_map=trip_map,
            recommendations=recommendations,
            raw=data,
        )
        obj.formatted = {"trace_id": trace_id, "body": body}
        return obj
 
 
 
 
def _hhmm_to_minutes(value: str) -> int:
    """Chuyển chuỗi 'HHMM' (ví dụ '1255') thành số phút (775)."""
    if not value:
        return 0
    value = str(value).zfill(4)
    try:
        hours = int(value[:-2])
        minutes = int(value[-2:])
        return hours * 60 + minutes
    except ValueError:
        return 0
 
 
def _hhmm_to_duration(value: str) -> str:
    """
    Chuyển chuỗi 'HHMM' thành dạng 'HHhMMm' dùng trong createBooking.
 
    Ví dụ: '0540' → '05h40m', '0205' → '02h05m', '1255' → '12h55m'.
    Trả về chuỗi rỗng nếu giá trị không hợp lệ.
    """
    if not value:
        return ""
    value = str(value).zfill(4)
    try:
        hh = value[:-2].zfill(2)
        mm = value[-2:].zfill(2)
        return f"{hh}h{mm}m"
    except (IndexError, ValueError):
        return ""
 
 
# Helpers cho from_dict → formatted body
# ─────────────────────────────────────────────────────────────────────────
 
def _find_recommendations_by_class_group(
    recommendations: list["Recommendation"],
    want_premium: bool,
) -> list["Recommendation"]:
    """
    Tìm TẤT CẢ recommendation có hạng vé (booking_class) của chiều đi
    (``list_fare[0]``) và chiều về (``list_fare[1]``, nếu là khứ hồi)
    đồng nhất về nhóm:

    - ``want_premium=True``  → cả 2 chiều đều thuộc PREMIUM_BOOKING_CLASSES
      (S, G, A, X).
    - ``want_premium=False`` → cả 2 chiều đều KHÔNG thuộc
      PREMIUM_BOOKING_CLASSES.

    Nếu 2 chiều lệch nhóm (1 bên premium, 1 bên không) thì recommendation
    đó không thỏa mãn cho cả 2 trường hợp trên → bỏ qua.

    Với vé một chiều (chỉ có ``list_fare[0]``), chỉ xét hạng đi.

    Trả về danh sách theo đúng thứ tự xuất hiện trong ``recommendations``
    (không dừng lại ở kết quả đầu tiên tìm thấy).
    """
    matches: list["Recommendation"] = []

    for rec in recommendations:
        adult = rec.adult_pricing
        if not adult or not adult.list_fare:
            continue

        outbound_class = adult.list_fare[0].booking_class
        outbound_is_premium = outbound_class in PREMIUM_BOOKING_CLASSES

        if len(adult.list_fare) >= 2:
            inbound_class = adult.list_fare[1].booking_class
            inbound_is_premium = inbound_class in PREMIUM_BOOKING_CLASSES

            # 2 chiều phải cùng nhóm (cùng premium hoặc cùng không) mới hợp lệ
            if outbound_is_premium != inbound_is_premium:
                continue

            if outbound_is_premium == want_premium:
                matches.append(rec)
        else:
            # Một chiều (OW): chỉ xét hạng đi
            if outbound_is_premium == want_premium:
                matches.append(rec)

    return matches


def _build_entries_from_recommendation(rec: "Recommendation") -> list[dict[str, Any]]:
    """
    Build danh sách entry (``chiều_đi`` / ``chiều_về`` / ``thông_tin_chung``)
    từ MỘT Recommendation cụ thể.

    Dùng chung cho cả:
    - Logic cũ: luôn build từ ``recommendation[0]``.
    - Logic mới (điểm đi là Hàn Quốc): build từ recommendation được chọn
      theo nhóm hạng vé (premium / normal) bởi
      :func:`_find_recommendation_by_class_group`.
    """
    entries: list[dict[str, Any]] = []
    adult = rec.adult_pricing

    # fare theo route (ICNHAN / HANICN) – dùng chung cho mọi cặp trong rec
    fare_outbound: RouteFare | None = None
    fare_inbound: RouteFare | None = None
    if adult:
        for fare in adult.list_fare:
            # Xác định chiều đi / chiều về dựa trên thứ tự list_fare
            if fare_outbound is None:
                fare_outbound = fare
            else:
                fare_inbound = fare

    for itinerary in rec.itineraries:
        trips = itinerary.trips

        if len(trips) == 0:
            continue

        if len(trips) >= 2:
            # ── Khứ hồi (RT): 2 trip trong list_trip ──────────────
            out_trip: Trip = trips[0]
            in_trip: Trip = trips[1]
            entry = {
                "chiều_đi":        _format_leg(out_trip, fare_outbound, trip_id=1),
                "chiều_về":        _format_leg(in_trip,  fare_inbound,  trip_id=2),
                "thông_tin_chung": _format_summary(fare_outbound, fare_inbound),
            }
        else:
            # ── Một chiều (OW): chỉ có 1 trip trong list_trip ─────
            only_trip: Trip = trips[0]
            entry = {
                "chiều_đi":        _format_leg(only_trip, fare_outbound, trip_id=1),
                "thông_tin_chung": _format_summary(fare_outbound, None),
            }

        entries.append(entry)

    return entries


def _parse_datetime(dt_str: str) -> tuple[str, str]:
    """
    Tách chuỗi datetime 'YYYY-MM-DD HH:MM:SS' thành (giờ 'HH:MM', ngày 'DD/MM/YYYY').
    Trả về ('', '') nếu parse lỗi.
    """
    if not dt_str:
        return "", ""
    try:
        date_part, time_part = dt_str.strip().split(" ", 1)
        year, month, day = date_part.split("-")
        hour, minute = time_part.split(":")[:2]
        return f"{hour}:{minute}", f"{day}/{month}/{year}"
    except (ValueError, IndexError):
        return "", ""
def _format_leg(trip: Trip, fare: "RouteFare | None", trip_id: int = 1) -> dict[str, Any]:
    """
    Tạo dict thông tin một chiều bay từ Trip + RouteFare.
 
    Cấu trúc output::
 
        {
            "hãng": "9G",
            "nơi_đi": "ICN",
            "nơi_đến": "HAN",
            "giờ_cất_cánh": "11:25",
            "ngày_cất_cánh": "18/07/2026",
            "thời_gian_bay": "0935",
            "giờ_hạ_cánh": "19:00",
            "ngày_hạ_cánh": "18/07/2026",
            "số_hiệu_máy_bay": "451",
            "số_điểm_dừng": "1",
            "điểm_dừng_1": "PQC",
            "loại_vé": "U",
            "giá_vé_gốc": 260800,
            "BookingKey": "UMELR0KA",
            "list_itinerary": [
                {
                    "trip_id": 1,
                    "segment_id": 1,
                    "departure": "ICN",
                    "arrival": "PQC",
                    "flight_date": "2026-08-14",
                    "flight_number": 455,
                    "elapse_flying_time": "1220",
                    "duration": "05h40m",
                    "carrier": "9G",
                    "booking_class": "O",
                    "fare_basis": "OMESR0KA",
                    "break_point": "N",
                    "flight_status": "NN"
                },
                ...
            ]
        }
    """
    first_seg = trip.segments[0] if trip.segments else None
    last_seg  = trip.segments[-1] if trip.segments else None
 
    dep_time, dep_date = _parse_datetime(first_seg.departure.datetime if first_seg else "")
    arr_time, arr_date = _parse_datetime(last_seg.arrival.datetime   if last_seg  else "")
 
    # Số hiệu chuyến bay chặng đầu (chặng chính)
    flight_number = str(first_seg.flight_number) if first_seg else ""
 
    # Carrier (hãng) từ segment đầu
    carrier = first_seg.carrier if first_seg else ""
 
    # Điểm dừng: lấy code arrival của từng segment trừ segment cuối
    stop_codes = [seg.arrival.code for seg in trip.segments[:-1]]
 
    # BookingKey = fare_basis của segment đầu trong fare (segment_fare[0])
    booking_key = ""
    booking_class = ""
    base_price: float = 0.0
 
    # Map segment_id -> SegmentFareInfo để tra booking_class + fare_basis
    seg_fare_map: dict[int, "SegmentFareInfo"] = {}
    if fare:
        booking_class = fare.booking_class
        base_price    = fare.total_amount
        if fare.segment_fare:
            booking_key = fare.segment_fare[0].fare_basis
        # Map theo thứ tự index (segment_id bắt đầu từ 1)
        for idx, sf in enumerate(fare.segment_fare, start=1):
            seg_fare_map[idx] = sf
 
    # ── Xây dựng list_itinerary cho createBooking ────────────────────────────
    # Cấu trúc mỗi phần tử khớp hoàn toàn với payload createBooking.
    # - duration: chuyển "HHMM" → "HHhMMm"  (e.g. "0540" → "05h40m")
    # - elapse_flying_time: giữ nguyên chuỗi "HHMM" của trip (tổng hành trình)
    # - break_point: "Y" cho segment cuối (end of route), "N" cho các segment trước
    # - flight_status: luôn "NN" (giá trị mặc định cho booking mới)
    list_itinerary: list[dict[str, Any]] = []
    num_segments = len(trip.segments)
    for seg_idx, seg in enumerate(trip.segments, start=1):
        sf = seg_fare_map.get(seg_idx)
        seg_booking_class = sf.booking_class if sf else booking_class
        seg_fare_basis    = sf.fare_basis    if sf else booking_key
        seg_break_point   = sf.break_point   if sf else ("Y" if seg_idx == num_segments else "N")
 
        list_itinerary.append({
            "trip_id":           trip_id,
            "segment_id":        seg_idx,
            "departure":         seg.departure.code,
            "arrival":           seg.arrival.code,
            "flight_date":       seg.flight_date,
            "flight_number":     int(seg.flight_number) if str(seg.flight_number).isdigit() else seg.flight_number,
            "elapse_flying_time": trip.elapse_flying_time,
            "duration":          _hhmm_to_duration(seg.duration),
            "carrier":           seg.carrier,
            "booking_class":     seg_booking_class,
            "fare_basis":        seg_fare_basis,
            "break_point":       seg_break_point,
            "flight_status":     "NN",
        })
 
    result: dict[str, Any] = {
        "hãng":            carrier,
        "nơi_đi":          trip.departure,
        "nơi_đến":         trip.arrival,
        "giờ_cất_cánh":    dep_time,
        "ngày_cất_cánh":   dep_date,
        "thời_gian_bay":   trip.elapse_flying_time,
        "giờ_hạ_cánh":     arr_time,
        "ngày_hạ_cánh":    arr_date,
        "số_hiệu_máy_bay": flight_number,
        "số_điểm_dừng":    str(trip.stop_number),
        "loại_vé":         booking_class,
        "giá_vé_gốc":      int(base_price),
        "BookingKey":      booking_key,
        "list_itinerary":  list_itinerary,
    }
 
    # Thêm điểm_dừng_N động
    for idx, code in enumerate(stop_codes, start=1):
        result[f"điểm_dừng_{idx}"] = code
 
    return result
 
 
def _format_summary(
    fare_out: "RouteFare | None",
    fare_in:  "RouteFare | None",
) -> dict[str, Any]:
    """
    Tạo dict thông_tin_chung: tổng giá, số ghế còn ít nhất, hành lý.
 
    ``số_ghế_còn`` lấy min seat_availability trong tất cả segment_fare
    của cả 2 chiều → con số an toàn nhất để hiển thị cho khách.
 
    ``hành_lý_vna`` = None vì Sun Portal không trả thông tin hành lý
    VNA riêng (chỉ có baggage_allowance.weight tính theo số kiện).
    """
    total = 0.0
    min_seat = 9  # mặc định max
 
    for fare in [fare_out, fare_in]:
        if fare is None:
            continue
        total += fare.total_amount
        for sf in fare.segment_fare:
            if sf.seat_availability < min_seat:
                min_seat = sf.seat_availability
 
    return {
        "giá_vé":     str(int(total)),
        "số_ghế_còn": str(min_seat),
        "hành_lý_vna": "None",
    }