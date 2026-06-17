"""
appSunPQ/models/hold.py
Models cho Hold Booking API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class HoldResult:
    """Kết quả giữ chỗ."""
    success: bool = False
    hold_id: str = ""
    booking_code: str = ""
    pnr: str = ""
    expire_time: str = ""
    amount_due: float = 0.0
    currency: str = "VND"
    status: str = ""
    message: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HoldResult":
        """Parse từ dict API response."""
        success = data.get("success", data.get("status") in ("success", "OK", "HOLD"))
        inner = data.get("data", data)

        return cls(
            success=success,
            hold_id=inner.get("holdId", inner.get("hold_id", inner.get("id", ""))),
            booking_code=inner.get("bookingCode", inner.get("booking_code", "")),
            pnr=inner.get("pnr", inner.get("PNR", "")),
            expire_time=inner.get("expireTime", inner.get("expire_time", inner.get("holdExpiry", ""))),
            amount_due=float(inner.get("amountDue", inner.get("amount_due", inner.get("totalAmount", 0)))),
            currency=inner.get("currency", "VND"),
            status=inner.get("status", ""),
            message=data.get("message", ""),
            raw=data,
        )
