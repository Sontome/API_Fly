"""
appSunPQ/models/confirm_price.py
Models cho Confirm Price API (POST /normal/create/confirm-price).

Mục đích: giá trả về trong /normal/search (recommendation.list_pax_pricing)
là giá GỢI Ý — server ghép sẵn theo từng route (ICNHAN / HANICN) riêng lẻ.
Sau khi đã chọn ra một tổ hợp itinerary cụ thể (OW: 1 chiều, RT: 2 chiều),
cần gọi confirm-price với ĐÚNG tổ hợp đó để lấy giá CHUẨN cuối cùng (giá có
thể tăng/giảm chút ít so với giá gợi ý ban đầu).

─────────────────────────────────────────────────────────────────────────────
Payload thật (ví dụ khứ hồi ICN <-> HAN, 1 chặng mỗi chiều)::

    {
        "list_itinerary": [
            {
                "trip_id": "ICNHAN-1",      # trip_id GỐC (chuỗi), KHÔNG phải 1/2
                "segment_id": 1,             # đánh số LIÊN TỤC toàn bộ itinerary
                "departure": "ICN",
                "arrival": "HAN",
                "flight_date": "2026-09-14",
                "flight_number": 411,
                "carrier": "9G",
                "booking_class": "V",
                "fare_basis": "VMELR0KF",
                "break_point": "N"
            },
            {
                "trip_id": "HANICN-1",
                "segment_id": 2,
                "departure": "HAN",
                "arrival": "ICN",
                "flight_date": "2026-09-25",
                "flight_number": 410,
                "carrier": "9G",
                "booking_class": "V",
                "fare_basis": "VMELR0KF",
                "break_point": "Y"
            }
        ],
        "adult": 1,
        "child": 0,
        "infant": 0,
        "option": {
            "direct_only": false,
            "flexible": false,
            "promo_code": "",
            "corporate_code": "",
            "trip_type": "RT",
            "currency": "KRW"
        }
    }

LƯU Ý QUAN TRỌNG khác với list_itinerary dùng cho create-booking:
    - "trip_id": trip_id GỐC dạng chuỗi (vd "ICNHAN-1"), không phải số 1/2.
    - "segment_id": đánh số LIÊN TỤC xuyên suốt toàn bộ itinerary (cả 2
      chiều nếu khứ hồi) — KHÔNG reset lại về 1 ở mỗi chiều.
    - Không có "elapse_flying_time", "duration", "flight_status".

Response thật::

    {
        "data": {
            "list_itinerary": [ {...segment (rút gọn)...}, ... ],
            "flight_fare": {
                "segment_fare": [
                    {"segment_id": 1, "fare_basis": "VMELR0KF", "booking_class": "V"},
                    {"segment_id": 2, "fare_basis": "VMELR0KF", "booking_class": "V"}
                ],
                "pax_pricing": [
                    {
                        "type": "ADULT",
                        "currency": "KRW",
                        "display_fare": 97000,
                        "display_fare_currency": "KRW",
                        "applied_fare": 97000,
                        "tax": 243300,
                        "base_fare": 97000,
                        "base_fare_currency": "KRW",
                        "total_amount": 340300,
                        "list_tax": [ {"code": "YQ", "amount": 179000, "country_code": "AC"}, ... ]
                    }
                ]
            }
        },
        "error": null,
        "success": true,
        "trace_id": "..."
    }

QUAN TRỌNG: với khứ hồi (RT), ``pax_pricing`` chỉ trả về MỘT tổng duy nhất
cho CẢ 2 chiều gộp lại (không tách riêng giá chiều đi / chiều về).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ─────────────────────────────────────────────────────────────────────────
# Payload builder
# ─────────────────────────────────────────────────────────────────────────

def build_confirm_price_payload(
    list_itinerary: list[dict[str, Any]],
    adult: int = 1,
    child: int = 0,
    infant: int = 0,
    trip_type: str = "RT",
    currency: str = "KRW",
    promo_code: str = "",
    corporate_code: str = "",
    direct_only: bool = False,
    flexible: bool = False,
) -> dict[str, Any]:
    """
    Build payload cho POST /normal/create/confirm-price.

    Args:
        list_itinerary: Danh sách segment ĐÚNG format confirm-price (xem
            docstring module) — dùng
            :func:`appSunPQ.models.search._build_confirm_itinerary` (nội bộ)
            để build từ kết quả search, KHÔNG dùng
            ``formatted["body"][i]["chiều_đi"]["list_itinerary"]`` (đó là
            format cho create-booking, khác trip_id/segment_id).
        adult/child/infant: Số lượng hành khách từng loại (phải khớp với
            search ban đầu).
        trip_type: "RT" hoặc "OW".
        currency: Mã tiền tệ.
        promo_code/corporate_code: Mã khuyến mãi / hợp đồng (nếu có).
        direct_only/flexible: Cờ tùy chọn, mặc định False.

    Returns:
        dict sẵn sàng POST lên API.
    """
    return {
        "list_itinerary": list_itinerary,
        "adult": adult,
        "child": child,
        "infant": infant,
        "option": {
            "direct_only": direct_only,
            "flexible": flexible,
            "promo_code": promo_code,
            "corporate_code": corporate_code,
            "trip_type": trip_type,
            "currency": currency,
        },
    }


# ─────────────────────────────────────────────────────────────────────────
# Output models — parse response
# ─────────────────────────────────────────────────────────────────────────

@dataclass
class ConfirmTaxInfo:
    """Một dòng thuế/phụ phí trong pax_pricing."""
    code: str = ""
    amount: float = 0.0
    country_code: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConfirmTaxInfo":
        return cls(
            code=data.get("code", ""),
            amount=float(data.get("amount", 0)),
            country_code=data.get("country_code", ""),
        )


@dataclass
class ConfirmPaxPricing:
    """Giá đã CONFIRM theo loại khách (ADULT / CHILD / INFANT)."""
    type: str = ""
    currency: str = "KRW"
    display_fare: float = 0.0
    applied_fare: float = 0.0
    base_fare: float = 0.0
    tax: float = 0.0
    total_amount: float = 0.0
    list_tax: list[ConfirmTaxInfo] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConfirmPaxPricing":
        return cls(
            type=data.get("type", ""),
            currency=data.get("currency", "KRW"),
            display_fare=float(data.get("display_fare", 0)),
            applied_fare=float(data.get("applied_fare", 0)),
            base_fare=float(data.get("base_fare", 0)),
            tax=float(data.get("tax", 0)),
            total_amount=float(data.get("total_amount", 0)),
            list_tax=[ConfirmTaxInfo.from_dict(t) for t in data.get("list_tax", [])],
        )


@dataclass
class ConfirmSegmentFare:
    """Hạng vé đã confirm cho 1 segment (segment_id liên tục)."""
    segment_id: int = 0
    fare_basis: str = ""
    booking_class: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConfirmSegmentFare":
        return cls(
            segment_id=data.get("segment_id", 0),
            fare_basis=data.get("fare_basis", ""),
            booking_class=data.get("booking_class", ""),
        )


@dataclass
class ConfirmPriceResult:
    """
    Kết quả từ POST /normal/create/confirm-price — giá CHUẨN cho 1 tổ hợp
    itinerary cụ thể (đã ghép sẵn cả chiều đi + chiều về nếu khứ hồi).

    LƯU Ý: với khứ hồi, ``total_amount`` / ``pax_pricing`` là TỔNG GỘP CẢ
    2 CHIỀU — không có giá tách riêng cho từng chiều.
    """
    success: bool = False
    error: Any = None
    trace_id: str = ""
    list_itinerary: list[dict[str, Any]] = field(default_factory=list)
    segment_fare: list[ConfirmSegmentFare] = field(default_factory=list)
    pax_pricing: list[ConfirmPaxPricing] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def adult_pricing(self) -> ConfirmPaxPricing | None:
        for p in self.pax_pricing:
            if p.type == "ADULT":
                return p
        return self.pax_pricing[0] if self.pax_pricing else None

    @property
    def total_amount(self) -> float:
        """Tổng tiền CHUẨN (ADULT) — dùng giá trị này để cập nhật lại kết quả search."""
        pricing = self.adult_pricing
        return pricing.total_amount if pricing else 0.0

    @property
    def currency(self) -> str:
        pricing = self.adult_pricing
        return pricing.currency if pricing else "KRW"

    @property
    def is_valid(self) -> bool:
        """True nếu confirm thành công VÀ có giá ADULT > 0."""
        return self.success and self.total_amount > 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConfirmPriceResult":
        success = bool(data.get("success", False))
        error = data.get("error")
        trace_id = data.get("trace_id", "")
        inner = data.get("data") or {}

        flight_fare = inner.get("flight_fare") or {}
        segment_fare = [
            ConfirmSegmentFare.from_dict(sf) for sf in flight_fare.get("segment_fare", [])
        ]
        pax_pricing = [
            ConfirmPaxPricing.from_dict(p) for p in flight_fare.get("pax_pricing", [])
        ]

        return cls(
            success=success,
            error=error,
            trace_id=trace_id,
            list_itinerary=inner.get("list_itinerary", []),
            segment_fare=segment_fare,
            pax_pricing=pax_pricing,
            raw=data,
        )
