"""
appSunPQ/endpoints.py
Danh sách endpoint của Sun Portal Agency API.

Base URL: https://agency-api-spa.sunportal.com.vn
"""

from __future__ import annotations

from appSunPQ.constants import API_BASE_URL

# ─── Search ─────────────────────────────────────────────────────────────────
# POST /normal/search
SEARCH_FLIGHT = f"{API_BASE_URL}/normal/search"

# POST /normal/search-minfare — tìm giá rẻ nhất trong khoảng day_interval ngày.
# Dùng làm endpoint kiểm tra session (nhẹ, ít side-effect hơn search thật).
SEARCH_MINFARE = f"{API_BASE_URL}/normal/search-minfare"

# ─── Session / Account ──────────────────────────────────────────────────────
# GET /normal/check-account-fund
#
# QUAN TRỌNG: phải dùng cùng domain (agency-api-spa) với mọi endpoint khác
# (SEARCH_FLIGHT, CREATE_BOOKING, HOLD_BOOKING, RETRIEVE_BOOKING). Token lấy
# từ Playwright login là token của agency-api-spa — không đảm bảo hợp lệ
# trên domain khác như master-api-spa. Trước đây endpoint này từng bị đổi
# nhầm sang "https://master-api-spa.sunportal.com.vn/api/common/auth/me",
# khiến _is_session_valid() trả về True (vì /auth/me 200 OK trên domain
# khác) ngay cả khi token đã hết hạn thật trên agency-api-spa — dẫn đến
# SessionManager không tự đăng nhập lại, và /normal/search vẫn 401.
CHECK_ACCOUNT_FUND = f"{API_BASE_URL}/normal/check-account-fund"

# ─── Hold booking ───────────────────────────────────────────────────────────
# POST /normal/create/hold-booking
HOLD_BOOKING = f"{API_BASE_URL}/normal/create/hold-booking"

# ─── Create booking / Issue ticket ─────────────────────────────────────────
# POST /normal/create/create-booking
CREATE_BOOKING = f"{API_BASE_URL}/normal/create/create-booking"

# ─── Manage booking ─────────────────────────────────────────────────────────
# POST /normal/manage/retrieve-booking
RETRIEVE_BOOKING = f"{API_BASE_URL}/normal/manage/retrieve-booking"
