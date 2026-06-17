"""
appSunPQ/models/booking.py
Models cho Create Booking + Hold Booking API.

Luồng thật:
    1. POST /normal/create/create-booking
       → response trả về trace_id + booking_status + list_itinerary + total_amount_tobe_paid
       → KHÔNG phải PNR — đây chỉ là bước xác nhận giá / itinerary

    2. POST /normal/create/hold-booking  (dùng trace_id từ bước 1)
       payload: {"trace_id": "FLN...", "option": {"send_email": "Y"}}
       → response mới trả về PNR + booking_code + ...

─────────────────────────────────────────────────────────────────────────────
Payload create-booking::

    {
        "list_itinerary": [ {segment...}, ... ],
        "list_passenger": [ {"pax_id":1,"type":"ADULT","first_name":"...","last_name":"...",...} ],
        "contact_info":   {"email":"...","phone_number":"...","full_name":"...","isValid":true},
        "option":         {"direct_only":false,"promo_code":"","corporate_code":"",
                           "trip_type":"RT","currency":"KRW"}
    }

Payload hold-booking::

    {
        "trace_id": "FLN202606151333301781505210793301563",
        "option":   {"send_email": "Y"}
    }
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Input models — build payload
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Passenger:
    """
    Thông tin một hành khách, dùng để build list_passenger trong payload.

    Attributes:
        pax_id:        ID thứ tự hành khách (bắt đầu từ 1).
        type:          Loại khách: "ADULT", "CHILD", "INFANT".
        first_name:    Tên (tự động .upper() khi to_dict).
        last_name:     Họ  (tự động .upper() khi to_dict).
        title:         Danh xưng. ADULT thường "MR"/"MRS"/"MS", CHILD "MSTR"/"MISS",
                       INFANT "MSTR"/"MISS". Để trống nếu không có.
        parent_id:     pax_id của hành khách ADULT đi kèm — BẮT BUỘC cho INFANT
                       (None nếu là ADULT/CHILD độc lập).
        date_of_birth: Ngày sinh "YYYY-MM-DD" — BẮT BUỘC cho CHILD và INFANT,
                       không dùng cho ADULT.

    Ví dụ::

        # ADULT
        Passenger(pax_id=1, type="ADULT", title="MR",
                  first_name="SON", last_name="TRINH")

        # CHILD — cần date_of_birth
        Passenger(pax_id=2, type="CHILD", title="MSTR",
                  first_name="VU", last_name="TRINH",
                  date_of_birth="2024-09-05")

        # INFANT — cần date_of_birth + parent_id (pax_id của ADULT đi kèm)
        Passenger(pax_id=3, type="INFANT", title="MISS",
                  first_name="KIM ANH", last_name="TRINH",
                  date_of_birth="2026-06-13", parent_id=1)
    """
    pax_id: int
    type: str              # "ADULT" | "CHILD" | "INFANT"
    first_name: str
    last_name: str
    title: str = ""
    parent_id: int | None = None
    date_of_birth: str | None = None

    def __post_init__(self) -> None:
        ptype = self.type.upper()
        if ptype in ("CHILD", "INFANT") and not self.date_of_birth:
            raise ValueError(
                f"Passenger pax_id={self.pax_id} type={ptype!r}: "
                "date_of_birth là bắt buộc cho CHILD và INFANT"
            )
        if ptype == "INFANT" and self.parent_id is None:
            raise ValueError(
                f"Passenger pax_id={self.pax_id} type=INFANT: "
                "parent_id là bắt buộc (pax_id của ADULT đi kèm)"
            )

    def to_dict(self) -> dict[str, Any]:
        """Chuyển thành dict đúng format list_passenger."""
        result: dict[str, Any] = {
            "pax_id":     self.pax_id,
            "type":       self.type.upper(),
            "title":      self.title,
            "first_name": self.first_name.upper(),
            "last_name":  self.last_name.upper(),
            "parent_id":  self.parent_id,
        }
        if self.date_of_birth:
            result["date_of_birth"] = self.date_of_birth
        return result


@dataclass
class ContactInfo:
    """
    Thông tin liên hệ cho booking.

    Attributes:
        email:        Email liên hệ.
        phone_number: Số điện thoại quốc tế (ví dụ "+84985422486").
        full_name:    Tên hiển thị (ví dụ "Mr Son HVA").
    """
    email: str
    phone_number: str
    full_name: str

    def to_dict(self) -> dict[str, Any]:
        """Chuyển thành dict đúng format contact_info."""
        return {
            "email":        self.email,
            "phone_number": self.phone_number,
            "full_name":    self.full_name,
            "isValid":      True,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Payload builders
# ─────────────────────────────────────────────────────────────────────────────

def build_booking_payload(
    list_itinerary: list[dict[str, Any]],
    list_passenger: list[Passenger] | list[dict[str, Any]],
    contact_info: ContactInfo | dict[str, Any],
    promo_code: str = "",
    corporate_code: str = "",
    currency: str = "KRW",
) -> dict[str, Any]:
    """
    Build payload cho POST /normal/create/create-booking.

    ``trip_type`` tự suy ra:
    - "RT" nếu list_itinerary chứa cả trip_id=1 và trip_id=2.
    - "OW" nếu chỉ có trip_id=1.

    Args:
        list_itinerary:  Danh sách segment bay ghép từ chiều đi + chiều về.
                         Lấy từ ``formatted["body"][i]["chiều_đi"]["list_itinerary"]``
                         + ``["chiều_về"]["list_itinerary"]`` (nếu RT).
        list_passenger:  list[Passenger] hoặc list[dict đã đúng format].
        contact_info:    ContactInfo hoặc dict.
        promo_code:      Mã khuyến mãi.
        corporate_code:  Mã hợp đồng.
        currency:        "KRW", "VND", ...

    Returns:
        dict sẵn sàng POST lên API.
    """
    pax_list: list[dict[str, Any]] = []
    for p in list_passenger:
        pax_list.append(p.to_dict() if isinstance(p, Passenger) else dict(p))

    if isinstance(contact_info, ContactInfo):
        contact_dict = contact_info.to_dict()
    else:
        contact_dict = dict(contact_info)
        contact_dict.setdefault("isValid", True)

    trip_ids = {seg.get("trip_id") for seg in list_itinerary}
    trip_type = "RT" if (1 in trip_ids and 2 in trip_ids) else "OW"

    return {
        "list_itinerary": list_itinerary,
        "list_passenger": pax_list,
        "contact_info":   contact_dict,
        "option": {
            "direct_only":    False,
            "promo_code":     promo_code,
            "corporate_code": corporate_code,
            "trip_type":      trip_type,
            "currency":       currency,
        },
    }


def build_hold_payload(
    trace_id: str,
    send_email: bool = True,
) -> dict[str, Any]:
    """
    Build payload cho POST /normal/create/hold-booking.

    Phải gọi sau create-booking và dùng trace_id từ BookingPreviewResult.

    Args:
        trace_id:    trace_id lấy từ ``BookingPreviewResult.trace_id``.
        send_email:  Gửi email xác nhận cho khách (mặc định True → "Y").

    Returns:
        {"trace_id": "FLN...", "option": {"send_email": "Y"}}

    Example::

        preview = client.create_booking_simple(...)
        payload = build_hold_payload(preview.trace_id)
        hold    = client.hold(payload)
        print(hold.pnr)
    """
    return {
        "trace_id": trace_id,
        "option":   {"send_email": "Y" if send_email else "N"},
    }


# ─────────────────────────────────────────────────────────────────────────────
# Output models — parse response
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PaxPricingResult:
    """Giá vé theo loại khách trong response create-booking."""
    type: str = ""
    currency: str = "KRW"
    applied_fare: float = 0.0
    base_fare: float = 0.0
    tax: float = 0.0
    total_amount: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PaxPricingResult":
        return cls(
            type=data.get("type", ""),
            currency=data.get("currency", "KRW"),
            applied_fare=float(data.get("applied_fare", 0)),
            base_fare=float(data.get("base_fare", 0)),
            tax=float(data.get("tax", 0)),
            total_amount=float(data.get("total_amount", 0)),
        )


@dataclass
class BookingPreviewResult:
    """
    Kết quả từ POST /normal/create/create-booking.

    Đây là bước XEM TRƯỚC (preview / confirm price) — chưa phải hold.
    Quan trọng nhất là ``trace_id`` để dùng cho bước hold tiếp theo.

    Luồng::

        preview = client.create_booking_simple(...)
        # preview.trace_id  → dùng cho hold_simple()
        # preview.booking_status  → "OK" nghĩa là giá hợp lệ
        # preview.total_amount    → tổng tiền cần thanh toán

        hold = client.hold_simple(preview.trace_id)
        print(hold.pnr)
    """
    success: bool = False
    trace_id: str = ""
    booking_status: str = ""          # "OK" = giá xác nhận, sẵn sàng hold
    total_amount: float = 0.0
    currency: str = "KRW"
    pax_pricing: list[PaxPricingResult] = field(default_factory=list)
    # Danh sách itinerary / hành khách phản hồi lại (dùng để kiểm tra)
    list_itinerary: list[dict[str, Any]] = field(default_factory=list)
    list_passenger: list[dict[str, Any]] = field(default_factory=list)
    error: Any = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def is_confirmed(self) -> bool:
        """True nếu server xác nhận giá OK và sẵn sàng hold."""
        return self.success and self.booking_status == "OK"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BookingPreviewResult":
        """
        Parse từ response thật của POST /normal/create/create-booking::

            {
                "data": {
                    "booking_status": "OK",
                    "flight_fare": {
                        "pax_pricing": [ {"type":"ADULT","total_amount":591900,...} ]
                    },
                    "list_itinerary": [...],
                    "list_passenger": [...],
                    "total_amount_tobe_paid": {"currency":"KRW","amount":591900}
                },
                "error": null,
                "success": true,
                "trace_id": "FLN202606151333301781505210793301563"
            }
        """
        success = bool(data.get("success", False))
        trace_id = data.get("trace_id", "")
        error = data.get("error")
        inner = data.get("data") or {}

        booking_status = inner.get("booking_status", "")

        # Tổng tiền thanh toán
        tobe_paid = inner.get("total_amount_tobe_paid") or {}
        total_amount = float(tobe_paid.get("amount", 0))
        currency = tobe_paid.get("currency", "KRW")

        # Giá theo loại khách
        flight_fare = inner.get("flight_fare") or {}
        pax_pricing = [
            PaxPricingResult.from_dict(p)
            for p in flight_fare.get("pax_pricing", [])
        ]

        return cls(
            success=success,
            trace_id=trace_id,
            booking_status=booking_status,
            total_amount=total_amount,
            currency=currency,
            pax_pricing=pax_pricing,
            list_itinerary=inner.get("list_itinerary", []),
            list_passenger=inner.get("list_passenger", []),
            error=error,
            raw=data,
        )


@dataclass
class TaxInfo:
    """Một dòng thuế/phụ phí trong pax_pricing."""
    code: str = ""
    amount: float = 0.0
    currency: str = "KRW"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaxInfo":
        return cls(
            code=data.get("code", ""),
            amount=float(data.get("amount", 0)),
            currency=data.get("currency", "KRW"),
        )


@dataclass
class PaxAmount:
    """Tiền phải trả theo từng hành khách, trong total_amount_tobe_paid.list_passenger."""
    pax_id: int | None = None
    parent_id: int | None = None
    type: str = ""
    amount: float = 0.0
    currency: str = "KRW"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PaxAmount":
        return cls(
            pax_id=data.get("pax_id"),
            parent_id=data.get("parent_id"),
            type=data.get("type", ""),
            amount=float(data.get("amount", 0)),
            currency=data.get("currency", "KRW"),
        )


@dataclass
class PassengerInfo:
    """Thông tin hành khách trong kết quả hold (response list_passenger)."""
    pax_id: int | None = None
    parent_id: int | None = None
    type: str = ""
    title: str = ""
    first_name: str = ""
    last_name: str = ""
    date_of_birth: str = ""
    status: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PassengerInfo":
        return cls(
            pax_id=data.get("pax_id"),
            parent_id=data.get("parent_id"),
            type=data.get("type", ""),
            title=data.get("title", ""),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            date_of_birth=data.get("date_of_birth", ""),
            status=data.get("status", ""),
        )


@dataclass
class BookingResult:
    """
    Kết quả từ POST /normal/create/hold-booking — bước GIỮ VÉ THẬT.

    Response thật::

        {
            "data": {
                "pnr_number": "FBF8CT",
                "booking_status": "OK",
                "expiration_date": "2026-06-19 17:28:00",
                "tz_expiration_date": "Asia/Seoul",
                "flight_fare": {"segment_fare": [...], "pax_pricing": [...]},
                "list_itinerary": [...],
                "list_passenger": [...],
                "contact_info": {...},
                "total_amount_tobe_paid": {
                    "currency": "KRW", "amount": 1535400,
                    "list_passenger": [{"pax_id":2,"type":"ADULT","amount":534000,...}, ...]
                },
                "created_at": "2026-06-16 08:31:00",
                ...
            },
            "error": null,
            "success": true,
            "trace_id": "FLN202606161528061781598486460308919"
        }
    """
    success: bool = False
    pnr: str = ""
    booking_status: str = ""
    trace_id: str = ""
    expiration_date: str = ""
    tz_expiration_date: str = ""
    time_purchase: str = ""
    tz_time_purchase: str = ""
    total_amount: float = 0.0
    currency: str = "KRW"
    pax_amounts: list[PaxAmount] = field(default_factory=list)
    pax_pricing: list[PaxPricingResult] = field(default_factory=list)
    list_itinerary: list[dict[str, Any]] = field(default_factory=list)
    passengers: list[PassengerInfo] = field(default_factory=list)
    contact_info: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    office_id: str = ""
    error: Any = None
    message: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def is_held(self) -> bool:
        """True nếu giữ vé thành công và có PNR."""
        return self.success and bool(self.pnr) and self.booking_status == "OK"

    @classmethod
    def from_dict(cls, data: dict[str, Any], status_code: int = 200) -> "BookingResult":
        """Parse từ response thật của POST /normal/create/hold-booking."""
        success = bool(data.get("success", status_code < 400))
        trace_id = data.get("trace_id", "")
        error = data.get("error")
        inner = data.get("data") or {}

        tobe_paid = inner.get("total_amount_tobe_paid") or {}
        total_amount = float(tobe_paid.get("amount", 0))
        currency = tobe_paid.get("currency", "KRW")
        pax_amounts = [
            PaxAmount.from_dict(p) for p in tobe_paid.get("list_passenger", [])
        ]

        flight_fare = inner.get("flight_fare") or {}
        pax_pricing = [
            PaxPricingResult.from_dict(p) for p in flight_fare.get("pax_pricing", [])
        ]

        passengers = [
            PassengerInfo.from_dict(p) for p in inner.get("list_passenger", [])
        ]

        return cls(
            success=success,
            pnr=inner.get("pnr_number", ""),
            booking_status=inner.get("booking_status", ""),
            trace_id=trace_id,
            expiration_date=inner.get("expiration_date", ""),
            tz_expiration_date=inner.get("tz_expiration_date", ""),
            time_purchase=inner.get("time_purchase", ""),
            tz_time_purchase=inner.get("tz_time_purchase", ""),
            total_amount=total_amount,
            currency=currency,
            pax_amounts=pax_amounts,
            pax_pricing=pax_pricing,
            list_itinerary=inner.get("list_itinerary", []),
            passengers=passengers,
            contact_info=inner.get("contact_info", {}),
            created_at=inner.get("created_at", ""),
            office_id=inner.get("office_id", ""),
            error=error,
            message=data.get("message", ""),
            raw=data,
        )


@dataclass
class ApiResponse:
    """Generic API response wrapper."""
    success: bool = False
    status_code: int = 200
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any], status_code: int = 200) -> "ApiResponse":
        return cls(
            success=data.get("success", status_code < 400),
            status_code=status_code,
            message=data.get("message", ""),
            data=data.get("data", {}),
            raw=data,
        )
