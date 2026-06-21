"""
domain_access.py
=================
Phân quyền hãng bay theo domain.

QUAN TRỌNG: module này KHÔNG tự viết lại logic load config từ Supabase.
Nó tái sử dụng nguyên hàm `load_domain_configs()` đã có sẵn trong
`backend_supabase_kakao.py`. Toàn bộ phần dưới đây chỉ là lớp tích hợp
(cache + guard + filter) được gọi vào đúng 1 lần lúc startup, và đọc lại
nhiều lần (không query Supabase) trong lúc xử lý request.

Luồng hoạt động
----------------
1. Lúc FastAPI startup -> gọi `load_rules()` một lần duy nhất.
   `load_rules()` gọi `load_domain_configs()` (backend_supabase_kakao.py)
   và lưu kết quả vào biến global `DOMAIN_RULES` (cache RAM).
2. Mỗi request -> đọc `request.headers["host"]`, chuẩn hoá bỏ phần
   `:port`, rồi tra trong `DOMAIN_RULES` (không query Supabase).
3. Domain không có config -> FULL ACCESS (không filter gì).
4. Domain có config -> chỉ những hãng nằm trong `enabled` mới được:
   - Tạo task search (chặn ngay từ đầu endpoint, trước khi gọi API hãng)
   - Giữ lại trong response (áp dụng riêng cho response gộp nhiều hãng
     của VNA v3 — xem `filter_vna_flights`)

Muốn đổi config trên Supabase có hiệu lực: restart lại uvicorn để
`load_rules()` chạy lại lúc startup (đúng như quy ước hiện tại của dự án).
"""

from __future__ import annotations

from typing import Optional, Set

from fastapi import HTTPException, Request, status

from backend_supabase_kakao import load_domain_configs

# ---------------------------------------------------------------------------
# Cache global — chỉ được GHI một lần duy nhất lúc FastAPI startup
# (xem load_rules()). Trong lúc xử lý request chỉ ĐỌC biến này.
# ---------------------------------------------------------------------------
DOMAIN_RULES: dict = {}

# "VNA" (dùng trong config_json trên Supabase, ví dụ: {"enabled": ["VJ","VNA"]})
# và "VN" (mã hãng thực tế xuất hiện trong field "hãng" của response VNA v3,
# xem backend_api_vna_v3.prase_flights) đại diện cho CÙNG MỘT hãng
# (Vietnam Airlines) -> coi là tương đương khi so khớp quyền.
_ALIASES = {
    "VNA": "VN",
}


def _canon(code: Optional[str]) -> str:
    """Chuẩn hoá mã hãng để so sánh (vd: 'VNA' và 'VN' coi là 1)."""
    code = (code or "").strip().upper()
    return _ALIASES.get(code, code)


# ---------------------------------------------------------------------------
# 1) Load config 1 lần duy nhất lúc startup
# ---------------------------------------------------------------------------

def load_rules() -> None:
    """
    Gọi DUY NHẤT 1 LẦN trong FastAPI startup event.

    Tái sử dụng `load_domain_configs()` có sẵn — không viết lại logic
    query Supabase ở đây.
    """
    global DOMAIN_RULES
    DOMAIN_RULES = load_domain_configs() or {}
    print(f"✅ [domain_access] Loaded {len(DOMAIN_RULES)} domain configs")


# ---------------------------------------------------------------------------
# 2) Xác định domain từ request, không query Supabase
# ---------------------------------------------------------------------------

def normalize_host(raw_host: Optional[str]) -> str:
    """'apiapp.hanvietair.com:8000' -> 'apiapp.hanvietair.com'"""
    if not raw_host:
        return ""
    return raw_host.split(":")[0].strip().lower()


def get_host_from_request(request: Request) -> str:
    return normalize_host(request.headers.get("host"))


def get_allowed_airlines(host: str) -> Optional[Set[str]]:
    """
    Trả về:
      - None        -> domain KHÔNG có config -> FULL ACCESS (không filter).
      - set([...])  -> domain bị giới hạn, chỉ các mã trong set được phép
                        (đã chuẩn hoá qua _canon).
    """
    cfg = DOMAIN_RULES.get(host)
    if not cfg:
        return None

    enabled = cfg.get("enabled")
    if not enabled:
        return None

    return {_canon(code) for code in enabled}


# ---------------------------------------------------------------------------
# 3) Guard — chặn TỪ ĐẦU endpoint, trước khi tạo task / gọi API hãng bay
# ---------------------------------------------------------------------------

def assert_airline_allowed(request: Request, airline_code: str) -> Optional[Set[str]]:
    """
    Gọi ngay đầu mỗi endpoint search, TRƯỚC khi tạo task / gọi API hãng.

    Nếu domain bị giới hạn và `airline_code` không nằm trong danh sách
    được phép -> raise HTTPException 403 ngay lập tức (không search,
    không gọi API hãng đó).

    Trả về allowed-set hiện tại (hoặc None nếu full access) để endpoint
    có thể tái sử dụng cho bước filter response (vd: VNA v3).
    """
    host = get_host_from_request(request)
    allowed = get_allowed_airlines(host)

    print(
        f"Host={host or '(unknown)'} | "
        f"Allowed airlines={sorted(allowed) if allowed is not None else 'FULL ACCESS'}"
    )

    if allowed is not None and _canon(airline_code) not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Domain '{host}' không được phép tìm kiếm hãng "
                f"'{airline_code}'"
            ),
        )

    return allowed


# ---------------------------------------------------------------------------
# 4) Filter response gộp nhiều hãng (VNA v3 — Other Airline)
# ---------------------------------------------------------------------------

def _hang_of(flight_item: dict) -> str:
    """Lấy mã hãng từ 1 phần tử kết quả VNA v3 (field 'hãng')."""
    leg = flight_item.get("chiều_đi") or flight_item.get("chiều_về") or {}
    return _canon(leg.get("hãng"))


def filter_vna_flights(flights: list, allowed: Optional[Set[str]]) -> list:
    """
    Áp dụng cho response dạng list của /vna/check-ve-v3
    (mỗi phần tử có "chiều_đi"/"chiều_về" -> "hãng": "VNA"/"QH"/"K6"/...).

    - allowed is None (full access) -> giữ nguyên toàn bộ, không filter.
    - allowed là set -> chỉ giữ các chuyến có hãng nằm trong allowed
      (VN/VNA luôn nằm trong allowed tại đây, vì endpoint đã chặn từ đầu
      bằng assert_airline_allowed trước khi gọi search VNA).
    """
    before = len(flights)

    if allowed is None:
        print(f"Before filter: {before} flights | After filter: {before} flights")
        return flights

    filtered = [f for f in flights if _hang_of(f) in allowed]

    print(f"Before filter: {before} flights | After filter: {len(filtered)} flights")
    return filtered
