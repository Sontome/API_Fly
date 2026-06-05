"""
routers/change_router.py
FastAPI router for VietJet flight change price quotation.
 
Endpoints:
    POST /change/quote  — nhận ChangeRequest, tự động chọn luồng
                          quote_single_leg hoặc quote_two_legs dựa vào input.
 
Validation rules:
    - Tất cả: pnr, dep, arr, dep_date, new_flight_no bắt buộc
    - Two-leg  (segdel=99): arr_date + new_flight_arr_no bắt buộc, arr_date phải >= dep_date
    - Single-leg           : segdel phải là 1 hoặc 2
                             arr_date và new_flight_arr_no KHÔNG được truyền vào
"""
 
from __future__ import annotations
 
import re
import sys
import os
from datetime import date

from pydantic_core.core_schema import str_schema
 
# Cho phép các module bên trong vietjet_change_price import lẫn nhau
# theo kiểu `from core.xxx` thay vì `from vietjet_change_price.core.xxx`
_pkg_dir = os.path.join(os.path.dirname(__file__), "..", "vietjet_change_price")
_pkg_dir = os.path.normpath(_pkg_dir)
if _pkg_dir not in sys.path:
    sys.path.insert(0, _pkg_dir)
 
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Any
 
from vietjet_change_price.core.exceptions import QuotationError, TokenExpiredError, TokenLoadError
from vietjet_change_price.core.session import VietjetSession
from vietjet_change_price.models.change_models import ChangeRequest
from vietjet_change_price.services.quotation_service import ChangeQuotationService
 
router = APIRouter(prefix="", tags=["Change Price"])
 
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
 
_IATA_RE = re.compile(r"^[A-Z]{3}$")
_DATE_FMT = "%Y-%m-%d"
_FLIGHT_NO_RE = re.compile(r"^[A-Z0-9]{2,3}\d{1,4}$")  # e.g. VJ961, BL123
_PNR_RE = re.compile(r"^[A-Z0-9]{6}$")
 
 
def _valid_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False
 
 
# ---------------------------------------------------------------------------
# Pydantic schema
# ---------------------------------------------------------------------------
 
class ChangeQuoteRequest(BaseModel):
    """
    Payload nhận vào endpoint POST /change/quote.
 
    Two-leg  (segdel = 99): truyền đủ arr_date + new_flight_arr_no
    Single-leg (segdel = 1|2): KHÔNG truyền arr_date / new_flight_arr_no
    """
 
    pnr: str = Field(..., description="Mã đặt chỗ 6 ký tự, e.g. 9ZFR8J")
    dep: str = Field(..., description="Mã IATA sân bay đi, e.g. ICN")
    arr: str = Field(..., description="Mã IATA sân bay đến, e.g. HAN")
    dep_date: str = Field(..., description="Ngày bay đi YYYY-MM-DD")
    new_flight_no: str = Field(..., description="Số hiệu chuyến bay mới chiều đi, e.g. VJ961")
 
    # Two-leg only
    arr_date: str | None = Field(
        default=None,
        description="[Two-leg] Ngày bay về YYYY-MM-DD. Bắt buộc khi segdel=99",
    )
    new_flight_arr_no: str | None = Field(
        default=None,
        description="[Two-leg] Số hiệu chuyến bay mới chiều về, e.g. VJ960. Bắt buộc khi segdel=99",
    )
    segdel: int = Field(
        ...,
        description="Loại thao tác: 1=đổi chiều đi, 2=đổi chiều về, 99=đổi cả 2 chiều",
    )
 
    # --- Field validators ---
 
    @field_validator("pnr")
    @classmethod
    def validate_pnr(cls, v: str) -> str:
        v = v.strip().upper()
        if not _PNR_RE.match(v):
            raise ValueError("PNR phải là 6 ký tự chữ hoa/số, e.g. 9ZFR8J")
        return v
 
    @field_validator("dep", "arr")
    @classmethod
    def validate_iata(cls, v: str) -> str:
        v = v.strip().upper()
        if not _IATA_RE.match(v):
            raise ValueError("Mã IATA phải gồm đúng 3 chữ cái in hoa, e.g. HAN")
        return v
 
    @field_validator("dep_date")
    @classmethod
    def validate_dep_date(cls, v: str) -> str:
        v = v.strip()
        if not _valid_date(v):
            raise ValueError("dep_date phải có định dạng YYYY-MM-DD")
        return v
 
    @field_validator("arr_date")
    @classmethod
    def validate_arr_date(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not _valid_date(v):
            raise ValueError("arr_date phải có định dạng YYYY-MM-DD")
        return v
 
    @field_validator("new_flight_no", "new_flight_arr_no")
    @classmethod
    def validate_flight_no(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().upper()
        if not _FLIGHT_NO_RE.match(v):
            raise ValueError(
                "Số hiệu chuyến bay không hợp lệ. "
                "Định dạng: 2-3 ký tự hãng + 1-4 chữ số, e.g. VJ961"
            )
        return v
 
    @field_validator("segdel")
    @classmethod
    def validate_segdel(cls, v: int) -> int:
        if v not in (1, 2, 99):
            raise ValueError("segdel phải là 1 (chiều đi), 2 (chiều về), hoặc 99 (cả 2 chiều)")
        return v
 
    # --- Cross-field validation ---
 
    @model_validator(mode="after")
    def validate_route_logic(self) -> "ChangeQuoteRequest":
        if self.dep == self.arr:
            raise ValueError("dep và arr không được trùng nhau")
 
        is_two_leg = self.segdel == 99
        has_arr_date = self.arr_date is not None
        has_arr_flight = self.new_flight_arr_no is not None
 
        if is_two_leg:
            errors: list[str] = []
            if not has_arr_date:
                errors.append("arr_date bắt buộc khi segdel=99")
            if not has_arr_flight:
                errors.append("new_flight_arr_no bắt buộc khi segdel=99")
            if errors:
                raise ValueError(" | ".join(errors))
 
            if self.arr_date and self.dep_date:
                if date.fromisoformat(self.arr_date) < date.fromisoformat(self.dep_date):
                    raise ValueError("arr_date phải >= dep_date")
 
        else:
            errors = []
            if has_arr_date:
                errors.append("arr_date không được truyền khi segdel != 99")
            if has_arr_flight:
                errors.append("new_flight_arr_no không được truyền khi segdel != 99")
            if errors:
                raise ValueError(" | ".join(errors))
 
        return self
 
 
# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------
 
class QuoteResponse(BaseModel):
    success: bool
    flow: str                      # "single_leg" | "two_legs"
    pnr: str
    data: dict[str, Any]
 
 
# ---------------------------------------------------------------------------
# Dependency: session
# ---------------------------------------------------------------------------
 
def get_session() -> VietjetSession:
    return VietjetSession(state_file="state.json")
 
 
# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------
 
@router.post(
    "/change-vj-pnr",
    response_model=QuoteResponse,
    summary="Lấy giá đổi chuyến bay VietJet",
    description=(
        "Nhận `ChangeQuoteRequest` và tự động chọn luồng:\n\n"
        "- `segdel=99` + `arr_date` + `new_flight_arr_no` → **quote_two_legs**\n"
        "- `segdel=1` hoặc `segdel=2` → **quote_single_leg**"
    ),
)
async def quote_change_price(body: ChangeQuoteRequest) -> QuoteResponse:
    change_request = ChangeRequest(
        pnr=body.pnr,
        dep=body.dep,
        arr=body.arr,
        dep_date=body.dep_date,
        new_flight_no=body.new_flight_no,
        arr_date=body.arr_date,
        new_flight_arr_no=body.new_flight_arr_no,
        segdel=body.segdel,
    )
 
    is_two_leg = body.segdel == 99
    flow_name = "two_legs" if is_two_leg else "single_leg"
 
    session = get_session()
    try:
        with session:
            service = ChangeQuotationService(session)
 
            if is_two_leg:
                result = service.quote_two_legs(change_request)
            else:
                result = service.quote_single_leg(change_request)
 
    except TokenLoadError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Không thể load token xác thực: {e}",
        )
    except TokenExpiredError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token hết hạn: {e}",
        )
    except QuotationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Luồng báo giá thất bại: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi không mong muốn: {e}",
        )
 
    return QuoteResponse(
        success=True,
        flow=flow_name,
        pnr=body.pnr,
        data=result,
    )
@router.post(
    "/pre-change-vj-pnr",
    
    summary="Lấy info pnr trước khi đổi vé",
    description=(
        "Nhận pnr 6 kí tự"
    ),
)
async def pre_change_vj_pnr(pnr: str):
    try :
        session = get_session()
        with session:
            service = ChangeQuotationService(session)
            result = service.pre_change_vj_pnr(pnr)
            return result
    except Exception as e:
        print(e)
        return None

