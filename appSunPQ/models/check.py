"""
appSunPQ/models/check.py
Model cho Retrieve/Check Booking API.

Endpoint: POST /normal/manage/retrieve-booking
Payload:  {"pnr_number": "FBX5UK"}

Response trả về có cùng cấu trúc với hold-booking (pnr_number,
booking_status, flight_fare, list_itinerary, list_passenger,
total_amount_tobe_paid, ...) — module này parse lại theo format
rút gọn riêng cho việc kiểm tra vé.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CheckResult:
    """
    Kết quả truy vấn booking từ POST /normal/manage/retrieve-booking.

    Output format::

        {
            "pnr": "FBX5UK",
            "status": "OK",
            "hang": "SPA",
            "tongbillgiagoc": 591700,
            "currency": "KRW",
            "paymentstatus": false,
            "hanthanhtoan": "2026-06-16 23:59:59",
            "chieudi": [...],
            "chieuve": [...],
            "passengers": [...]
        }
    """
    pnr: str = ""
    status: str = ""
    hang: str = "SPA"
    tongbillgiagoc: float = 0.0
    currency: str = "KRW"
    paymentstatus: bool = False
    hanthanhtoan: str = ""
    chieudi: list[dict[str, Any]] = field(default_factory=list)
    chieuve: list[dict[str, Any]] = field(default_factory=list)
    passengers: list[dict[str, Any]] = field(default_factory=list)
    error: Any = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def is_ticketed(self) -> bool:
        """True nếu booking đã thanh toán/xuất vé thành công."""
        return self.paymentstatus is True

    def to_dict(self) -> dict[str, Any]:
        """Chuyển thành dict đúng format output mong muốn."""
        return {
            "pnr":            self.pnr,
            "status":         self.status,
            "hang":           self.hang,
            "tongbillgiagoc": self.tongbillgiagoc,
            "currency":       self.currency,
            "paymentstatus":  self.paymentstatus,
            "hanthanhtoan":   self.hanthanhtoan,
            "chieudi":        self.chieudi,
            "chieuve":        self.chieuve,
            "passengers":     self.passengers,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], status_code: int = 200) -> "CheckResult":
        """
        Parse từ response thật của POST /normal/manage/retrieve-booking::

            {
                "data": {
                    "pnr_number": "FBX5UK",
                    "booking_status": "OK",
                    "expiration_date": "2026-06-19 18:11:00",
                    "time_purchase": "2026-06-16 23:59:59",
                    "flight_fare": {"pax_pricing": [...]},
                    "list_itinerary": [
                        {"trip_id": 6, "segment_id": 3, "flight_date": "2026-08-14", ...},
                        {"trip_id": 6, "segment_id": 4, "flight_date": "2026-08-14", ...},
                        {"trip_id": 5, "segment_id": 1, "flight_date": "2026-08-22", ...},
                        {"trip_id": 5, "segment_id": 2, "flight_date": "2026-08-22", ...},
                    ],
                    "list_passenger": [...],
                    "total_amount_tobe_paid": {"currency": "KRW", "amount": 591700, ...},
                    ...
                },
                "error": null,
                "success": true,
                "trace_id": "FLN..."
            }

        Lưu ý: "chiều đi" / "chiều về" được tách dựa theo flight_date
        sớm nhất / muộn nhất trong list_itinerary (không dựa vào trip_id,
        vì server có thể trả trip_id theo thứ tự bất kỳ — như ví dụ thật
        ở trên, trip_id=6 là chiều đi nhưng xuất hiện trước trip_id=5).
        """
        success = bool(data.get("success", status_code < 400))
        error = data.get("error")
        inner = data.get("data") or {}

        pnr = inner.get("pnr_number", "")
        status = inner.get("booking_status", "")

        tobe_paid = inner.get("total_amount_tobe_paid") or {}
        tongbillgiagoc = float(tobe_paid.get("amount", 0))
        currency = tobe_paid.get("currency", "KRW")

        hanthanhtoan = inner.get("time_purchase", "") or inner.get("expiration_date", "")

        # Trạng thái thanh toán: payment_status không có sẵn trong response
        # mẫu -> coi như True khi server trả "ISSUED"/"PAID"/"TICKETED",
        # còn "OK" (chỉ mới hold/giữ chỗ) nghĩa là chưa thanh toán.
        payment_status_raw = inner.get("payment_status")
        if payment_status_raw is None:
            paymentstatus = status.upper() in ("ISSUED", "PAID", "TICKETED")
        else:
            paymentstatus = bool(payment_status_raw)

        list_itinerary = inner.get("list_itinerary", [])

        # ── Tách chiều đi / chiều về theo flight_date ────────────────────────
        chieudi: list[dict[str, Any]] = []
        chieuve: list[dict[str, Any]] = []
        if list_itinerary:
            # Nhóm segment theo trip_id, giữ nguyên thứ tự segment_id
            trips: dict[int, list[dict[str, Any]]] = {}
            for seg in list_itinerary:
                trips.setdefault(seg.get("trip_id"), []).append(seg)
            for tid, segs in trips.items():
                segs.sort(key=lambda s: s.get("segment_id", 0))

            # Sắp xếp các trip theo flight_date của segment đầu (sớm nhất → muộn nhất)
            ordered_trip_ids = sorted(
                trips.keys(),
                key=lambda tid: trips[tid][0].get("flight_date", ""),
            )

            if len(ordered_trip_ids) >= 1:
                chieudi = trips[ordered_trip_ids[0]]
            if len(ordered_trip_ids) >= 2:
                chieuve = trips[ordered_trip_ids[1]]

        passengers = inner.get("list_passenger", [])

        return cls(
            pnr=pnr,
            status=status,
            hang="SPA",
            tongbillgiagoc=tongbillgiagoc,
            currency=currency,
            paymentstatus=paymentstatus,
            hanthanhtoan=hanthanhtoan,
            chieudi=chieudi,
            chieuve=chieuve,
            passengers=passengers,
            error=error,
            raw=data,
        )
