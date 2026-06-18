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

# ─── Session / Account ──────────────────────────────────────────────────────
# GET /normal/check-account-fund
CHECK_ACCOUNT_FUND = f"https://agency-cms-spa.sunportal.com.vn/api/banner/list?type=homepage"

# ─── Hold booking ───────────────────────────────────────────────────────────
# POST /normal/create/hold-booking
HOLD_BOOKING = f"{API_BASE_URL}/normal/create/hold-booking"

# ─── Create booking / Issue ticket ─────────────────────────────────────────
# POST /normal/create/create-booking
CREATE_BOOKING = f"{API_BASE_URL}/normal/create/create-booking"

# ─── Manage booking ─────────────────────────────────────────────────────────
# POST /normal/manage/retrieve-booking
RETRIEVE_BOOKING = f"{API_BASE_URL}/normal/manage/retrieve-booking"
