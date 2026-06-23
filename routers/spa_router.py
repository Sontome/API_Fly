"""
routers/spa_router.py
FastAPI router cho Sun Portal flight search / booking / hold / check.

Endpoints:
    POST /spa/search        — tìm kiếm chuyến bay (search_simple)
    POST /spa/booking       — tạo booking + giữ vé luôn trong 1 lần gọi
                              (create_booking_simple → hold_simple)
    POST /spa/check         — tra cứu booking theo PNR (check_booking_simple)

Validation rules:
    - search:   dep_date bắt buộc YYYY-MM-DD; arr_date bắt buộc nếu trip_type="RT"
                và phải >= dep_date; dep != arr
    - booking:  list_itinerary phải có ít nhất 1 segment với trip_id hợp lệ (1 hoặc 1+2);
                list_passenger phải có ít nhất 1 hành khách
    - check:    pnr phải đúng 6 ký tự chữ hoa/số
"""

from __future__ import annotations

import re
import sys
import os
from datetime import date
from typing import Any

# Cho phép import `from appSunPQ.xxx` / `from shared.xxx` dù file này nằm
# trong routers/ — chèn project root vào sys.path.
_pkg_dir = os.path.join(os.path.dirname(__file__), "..")
_pkg_dir = os.path.normpath(_pkg_dir)
if _pkg_dir not in sys.path:
    sys.path.insert(0, _pkg_dir)

# Load .env từ project root (cùng cấp main.py) bằng đường dẫn TUYỆT ĐỐI,
# không phụ thuộc working directory lúc chạy (uvicorn, IDE, terminal khác
# thư mục, ...). Nếu không làm vậy, load_dotenv() mặc định chỉ tìm .env
# từ CWD — dễ thất bại âm thầm khi spa_router.py nằm trong routers/ và
# server được khởi động từ nơi khác.
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(_pkg_dir, ".env")
    load_dotenv(dotenv_path=_env_path, override=False)
except ImportError:
    pass

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator, model_validator
from starlette.concurrency import run_in_threadpool

from appSunPQ.client import SunPortalClient
from appSunPQ.models.booking import ContactInfo, Passenger
from appSunPQ.models.minfare import MinFareResult
from domain_access import assert_airline_allowed
from shared.exceptions import (
    BookingError,
    CheckBookingError,
    ConfigurationError,
    HoldError,
    SearchError,
    SessionExpiredError,
)

router = APIRouter(prefix="/spa", tags=["Sun Portal"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_IATA_RE = re.compile(r"^[A-Z]{3}$")
_PNR_RE = re.compile(r"^[A-Z0-9]{5,8}$")


def _valid_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Dependency: client
# ---------------------------------------------------------------------------

def _make_client() -> SunPortalClient:
    """
    Tạo SunPortalClient (sync, blocking).

    QUAN TRỌNG: hàm này PHẢI được gọi qua ``get_client_async()`` (chạy trong
    threadpool), KHÔNG được gọi trực tiếp từ trong một hàm ``async def``.

    Lý do: ``SessionManager.initialize()`` có thể trigger
    ``PlaywrightLoginService.login()``, dùng Playwright **Sync API**
    (``sync_playwright()``). Sync API của Playwright không tương thích với
    asyncio event loop — nếu gọi trực tiếp trong endpoint ``async def``,
    sẽ crash với lỗi:

        playwright._impl._errors.Error: It looks like you are using
        Playwright Sync API inside the asyncio loop.

    Chạy trong threadpool (qua ``run_in_threadpool``) đưa toàn bộ đoạn code
    sync này vào một thread riêng, không có event loop, nên Playwright Sync
    API chạy bình thường mà không block event loop chính của FastAPI.
    """
    try:
        return SunPortalClient(headless=True, auto_init=True)
    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"Chưa cấu hình tài khoản Sun Portal: {e}. "
                "Cần đặt SUNPORTAL_USERNAME, SUNPORTAL_PASSWORD, AGENTCYCODE "
                "trong .env (hoặc đảm bảo sunportal_state.json còn hiệu lực)."
            ),
        )


async def get_client_async() -> SunPortalClient:
    """
    Dependency async — tạo SunPortalClient trong threadpool.

    Dùng hàm này (KHÔNG dùng ``_make_client()`` trực tiếp) trong mọi
    endpoint ``async def`` để tránh lỗi Playwright Sync API trong asyncio
    loop. Mỗi request vẫn dùng instance client riêng (không cache/singleton),
    nhưng phần khởi tạo blocking (HTTP requests đồng bộ, Playwright login
    khi cần) chạy trên thread phụ.
    """
    return await run_in_threadpool(_make_client)


# ---------------------------------------------------------------------------
# Schema: /spa/search
# ---------------------------------------------------------------------------

class SearchQuoteRequest(BaseModel):
    """
    Payload nhận vào POST /spa/search.

    trip_type="RT" (khứ hồi): bắt buộc truyền arr_date.
    trip_type="OW" (một chiều): không cần arr_date.
    """

    departure: str = Field(..., description="Mã IATA sân bay đi, e.g. ICN")
    arrival: str = Field(..., description="Mã IATA sân bay đến, e.g. HAN")
    dep_date: str = Field(..., description="Ngày bay đi YYYY-MM-DD")
    arr_date: str | None = Field(
        default=None,
        description="Ngày bay về YYYY-MM-DD. Bắt buộc khi trip_type='RT'",
    )
    trip_type: str = Field(default="RT", description="'RT' (khứ hồi) hoặc 'OW' (một chiều)")
    adt: int = Field(default=1, ge=1, le=9, description="Số người lớn")
    chd: int = Field(default=0, ge=0, le=9, description="Số trẻ em")
    inf: int = Field(default=0, ge=0, le=9, description="Số trẻ sơ sinh")
    promo_code: str = Field(default="", description="Mã khuyến mãi (nếu có)")
    currency: str = Field(default="KRW", description="Tiền tệ, e.g. KRW, VND")

    @field_validator("departure", "arrival")
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

    @field_validator("trip_type")
    @classmethod
    def validate_trip_type(cls, v: str) -> str:
        v = v.strip().upper()
        if v not in ("RT", "OW"):
            raise ValueError("trip_type phải là 'RT' hoặc 'OW'")
        return v

    @model_validator(mode="after")
    def validate_route_logic(self) -> "SearchQuoteRequest":
        if self.departure == self.arrival:
            raise ValueError("departure và arrival không được trùng nhau")

        if self.trip_type == "RT":
            if not self.arr_date:
                raise ValueError("arr_date bắt buộc khi trip_type='RT'")
            if date.fromisoformat(self.arr_date) < date.fromisoformat(self.dep_date):
                raise ValueError("arr_date phải >= dep_date")
        else:
            if self.arr_date is not None:
                raise ValueError("arr_date không được truyền khi trip_type='OW'")

        return self


class SearchQuoteResponse(BaseModel):
    success: bool
    total_count: int
    data: dict[str, Any]


# ---------------------------------------------------------------------------
# Schema: /spa/booking  (create-booking + hold-booking trong 1 lần gọi)
# ---------------------------------------------------------------------------

class PassengerInput(BaseModel):
    """
    Một hành khách trong payload booking.

    - ADULT:  không cần date_of_birth / parent_id.
    - CHILD:  date_of_birth bắt buộc (YYYY-MM-DD).
    - INFANT: date_of_birth + parent_id (pax_id của ADULT đi kèm) bắt buộc.
    """

    pax_id: int = Field(..., ge=1, description="ID thứ tự hành khách, bắt đầu từ 1")
    type: str = Field(..., description="'ADULT' | 'CHILD' | 'INFANT'")
    first_name: str = Field(..., min_length=1, description="Tên, e.g. SON")
    last_name: str = Field(..., min_length=1, description="Họ, e.g. TRINH")
    title: str = Field(default="", description="Danh xưng, e.g. MR/MRS/MSTR/MISS")
    parent_id: int | None = Field(
        default=None,
        description="pax_id của ADULT đi kèm — BẮT BUỘC cho INFANT",
    )
    date_of_birth: str | None = Field(
        default=None,
        description="Ngày sinh YYYY-MM-DD — BẮT BUỘC cho CHILD và INFANT",
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        v = v.strip().upper()
        if v not in ("ADULT", "CHILD", "INFANT"):
            raise ValueError("type phải là 'ADULT', 'CHILD', hoặc 'INFANT'")
        return v

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not _valid_date(v):
            raise ValueError("date_of_birth phải có định dạng YYYY-MM-DD")
        return v

    @model_validator(mode="after")
    def validate_age_fields(self) -> "PassengerInput":
        if self.type in ("CHILD", "INFANT") and not self.date_of_birth:
            raise ValueError(
                f"pax_id={self.pax_id} type={self.type}: "
                "date_of_birth là bắt buộc cho CHILD và INFANT"
            )
        if self.type == "INFANT" and self.parent_id is None:
            raise ValueError(
                f"pax_id={self.pax_id} type=INFANT: "
                "parent_id là bắt buộc (pax_id của ADULT đi kèm)"
            )
        if self.type == "ADULT" and self.date_of_birth is not None:
            raise ValueError(
                f"pax_id={self.pax_id} type=ADULT: "
                "date_of_birth không được truyền cho ADULT"
            )
        return self


class ContactInfoInput(BaseModel):
    """Thông tin liên hệ trong payload booking."""

    email: str = Field(..., description="Email liên hệ")
    phone_number: str = Field(..., description="Số điện thoại dạng quốc tế, e.g. +84985422486")
    full_name: str = Field(..., min_length=1, description="Tên hiển thị, e.g. Mr Son HVA")


class ItinerarySegmentInput(BaseModel):
    """Một segment bay trong list_itinerary (lấy trực tiếp từ kết quả /spa/search)."""

    trip_id: int = Field(..., description="1 = chiều đi, 2 = chiều về")
    segment_id: int
    departure: str
    arrival: str
    flight_date: str
    flight_number: int
    elapse_flying_time: str
    duration: str
    carrier: str
    booking_class: str
    fare_basis: str
    break_point: str
    flight_status: str = "NN"

    @field_validator("trip_id")
    @classmethod
    def validate_trip_id(cls, v: int) -> int:
        if v not in (1, 2):
            raise ValueError("trip_id phải là 1 (chiều đi) hoặc 2 (chiều về)")
        return v


class BookingQuoteRequest(BaseModel):
    """
    Payload nhận vào POST /spa/booking.

    Gộp 2 bước thật của Sun Portal trong 1 lần gọi:
        1. create-booking → xác nhận giá, nhận trace_id
        2. hold-booking   → giữ vé thật, nhận PNR

    list_itinerary lấy trực tiếp từ kết quả /spa/search::

        body = search_result["data"]["formatted"]["body"][0]
        itin = body["chiều_đi"]["list_itinerary"] + body["chiều_về"]["list_itinerary"]
    """

    list_itinerary: list[ItinerarySegmentInput] = Field(
        ..., min_length=1, description="Ghép chiều đi + chiều về, lấy từ kết quả search"
    )
    list_passenger: list[PassengerInput] = Field(..., min_length=1)
    contact_info: ContactInfoInput
    promo_code: str = Field(default="", description="Mã khuyến mãi (nếu có)")
    corporate_code: str = Field(default="", description="Mã hợp đồng công ty (nếu có)")
    currency: str = Field(default="KRW")
    send_email: bool = Field(default=True, description="Gửi email xác nhận khi giữ vé thành công")

    @model_validator(mode="after")
    def validate_trip_ids(self) -> "BookingQuoteRequest":
        trip_ids = {seg.trip_id for seg in self.list_itinerary}
        if not trip_ids.issubset({1, 2}) or 1 not in trip_ids:
            raise ValueError("list_itinerary phải chứa trip_id=1 (và tùy chọn trip_id=2)")
        return self

    @model_validator(mode="after")
    def validate_infant_parent_links(self) -> "BookingQuoteRequest":
        adult_pax_ids = {p.pax_id for p in self.list_passenger if p.type == "ADULT"}
        for p in self.list_passenger:
            if p.type == "INFANT" and p.parent_id not in adult_pax_ids:
                raise ValueError(
                    f"pax_id={p.pax_id} type=INFANT: parent_id={p.parent_id} "
                    "không khớp pax_id của bất kỳ hành khách ADULT nào trong list_passenger"
                )
        return self


class BookingQuoteResponse(BaseModel):
    success: bool
    pnr: str
    booking_status: str
    trace_id: str
    expiration_date: str
    total_amount: float
    currency: str
    is_held: bool
    data: dict[str, Any]


# ---------------------------------------------------------------------------
# Schema: /spa/check
# ---------------------------------------------------------------------------

class CheckQuoteRequest(BaseModel):
    """Payload nhận vào POST /spa/check."""

    pnr: str = Field(..., description="Mã PNR cần tra cứu, e.g. FBX5UK")

    @field_validator("pnr")
    @classmethod
    def validate_pnr(cls, v: str) -> str:
        v = v.strip().upper()
        if not _PNR_RE.match(v):
            raise ValueError("pnr phải là 5-8 ký tự chữ hoa/số, e.g. FBX5UK")
        return v


class CheckQuoteResponse(BaseModel):
    success: bool
    data: dict[str, Any]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/check-ve-v3",
    response_model=SearchQuoteResponse,
    summary="Tìm kiếm chuyến bay Sun Portal + giá rẻ theo ngày",
    description=(
        "Nhận `SearchQuoteRequest` và gọi `search_simple`. "
        "Trả về danh sách gói bay đã format (chiều_đi / chiều_về / thông_tin_chung), "
        "mỗi gói có sẵn `list_itinerary` để dùng trực tiếp cho `/spa/booking`.\n\n"
        "Đồng thời gọi thêm `search-minfare` để lấy giá rẻ nhất ±7 ngày:\n\n"
        "- OW: 1 lần cho chiều đi.\n"
        "- RT: 2 lần riêng biệt (chiều đi + chiều về).\n\n"
        "Kết quả trả thêm trường `lowerfare` trong `data`:\n\n"
        "```json\n"
        "{\"lowerfare\": {\"chiều đi\": [{\"ngày\": \"14/08/2026\", \"giá_vé_gốc\": 273400}], "
        "\"chiều về\": [...]}}\n"
        "```"
    ),
)
async def search_flights(body: SearchQuoteRequest, request: Request) -> SearchQuoteResponse:
    assert_airline_allowed(request, "SUNPQ")
    client = await get_client_async()

    # ── Bước 1: search_simple ─────────────────────────────────────────────
    try:
        result = await run_in_threadpool(
            client.search_simple,
            departure=body.departure,
            arrival=body.arrival,
            depdate=body.dep_date,
            arrdate=body.arr_date,
            trip_type=body.trip_type,
            adt=body.adt,
            chd=body.chd,
            inf=body.inf,
            promo_code=body.promo_code,
            currency=body.currency,
        )
    except SessionExpiredError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Session hết hạn: {e}",
        )
    except SearchError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Tìm kiếm thất bại: {e}",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi không mong muốn: {e}",
        )

    # ── Bước 2: search_minfare — chạy song song với threadpool ───────────
    # Lỗi minfare không chặn kết quả search chính, chỉ trả list rỗng.
    lowerfare_out: list[dict[str, Any]] = []
    lowerfare_in: list[dict[str, Any]] = []

    try:
        mf_out: MinFareResult = await run_in_threadpool(
            client.search_minfare_simple,
            departure=body.departure,
            arrival=body.arrival,
            flight_date=body.dep_date,
            adult=body.adt,
            child=body.chd,
            infant=body.inf,
            currency=body.currency,
        )
        lowerfare_out = mf_out.to_list()
    except Exception:
        pass  # minfare lỗi -> giữ list rỗng, không block kết quả

    if body.trip_type == "RT" and body.arr_date:
        try:
            mf_in: MinFareResult = await run_in_threadpool(
                client.search_minfare_simple,
                departure=body.arrival,   # chiều về: đảo dep/arr
                arrival=body.departure,
                flight_date=body.arr_date,
                adult=body.adt,
                child=body.chd,
                infant=body.inf,
                currency=body.currency,
            )
            lowerfare_in = mf_in.to_list()
        except Exception:
            pass

    # ── Gộp lowerfare vào data ────────────────────────────────────────────
    formatted = result.formatted
    formatted["lowerfare"] = {
        "chiều đi": lowerfare_out,
        "chiều về": lowerfare_in,
    }

    return SearchQuoteResponse(
        success=True,
        total_count=result.total_count,
        data=formatted,
    )


@router.post(
    "/booking",
    response_model=BookingQuoteResponse,
    summary="Tạo booking và giữ vé (create-booking + hold-booking)",
    description=(
        "Nhận `BookingQuoteRequest` (list_itinerary lấy từ `/spa/search`), "
        "tự động chạy 2 bước thật của Sun Portal:\n\n"
        "1. **create-booking** — xác nhận giá, nhận `trace_id`\n"
        "2. **hold-booking** — giữ vé thật, nhận **PNR**\n\n"
        "Nếu bước 1 không xác nhận được giá (`is_confirmed=False`), "
        "endpoint dừng lại và trả lỗi 422 — không gọi hold-booking."
    ),
)
async def create_and_hold_booking(body: BookingQuoteRequest) -> BookingQuoteResponse:
    client = await get_client_async()

    list_itinerary = [seg.model_dump() for seg in body.list_itinerary]
    list_passenger = [
        Passenger(
            pax_id=p.pax_id, type=p.type, title=p.title,
            first_name=p.first_name, last_name=p.last_name,
            parent_id=p.parent_id, date_of_birth=p.date_of_birth,
        )
        for p in body.list_passenger
    ]
    contact_info = ContactInfo(
        email=body.contact_info.email,
        phone_number=body.contact_info.phone_number,
        full_name=body.contact_info.full_name,
    )

    try:
        # ── Bước 1: create-booking — xác nhận giá ────────────────────────────
        preview = await run_in_threadpool(
            client.create_booking_simple,
            list_itinerary=list_itinerary,
            list_passenger=list_passenger,
            contact_info=contact_info,
            promo_code=body.promo_code,
            corporate_code=body.corporate_code,
            currency=body.currency,
        )

        if not preview.is_confirmed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Không xác nhận được giá: booking_status="
                    f"{preview.booking_status!r}, trace_id={preview.trace_id!r}"
                ),
            )

        # ── Bước 2: hold-booking — giữ vé thật, lấy PNR ──────────────────────
        hold = await run_in_threadpool(
            client.hold_simple,
            trace_id=preview.trace_id,
            send_email=body.send_email,
        )

    except HTTPException:
        raise
    except SessionExpiredError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Session hết hạn: {e}",
        )
    except BookingError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Create booking thất bại: {e}",
        )
    except HoldError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Hold booking thất bại: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi không mong muốn: {e}",
        )

    if not hold.is_held:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Giữ vé thất bại: booking_status={hold.booking_status!r}",
        )

    return BookingQuoteResponse(
        success=True,
        pnr=hold.pnr,
        booking_status=hold.booking_status,
        trace_id=hold.trace_id,
        expiration_date=hold.expiration_date,
        total_amount=hold.total_amount,
        currency=hold.currency,
        is_held=hold.is_held,
        data=hold.raw,
    )


@router.post(
    "/checkpnr",
    response_model=CheckQuoteResponse,
    summary="Tra cứu booking theo PNR",
    description="Nhận `CheckQuoteRequest` (mã PNR) và gọi `check_booking_simple`.",
)
async def check_booking(body: CheckQuoteRequest) -> CheckQuoteResponse:
    client = await get_client_async()
    try:
        result = await run_in_threadpool(client.check_booking_simple, body.pnr)
    except SessionExpiredError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Session hết hạn: {e}",
        )
    except CheckBookingError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Tra cứu booking thất bại: {e}",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi không mong muốn: {e}",
        )

    return CheckQuoteResponse(success=True, data=result.to_dict())
