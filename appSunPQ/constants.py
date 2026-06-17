"""
appSunPQ/constants.py
Hằng số dùng chung cho toàn bộ module Sun Portal.
"""

from __future__ import annotations

import os

# ─── Đường dẫn ──────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(PROJECT_ROOT, "sunportal_state.json")

# ─── Domain / Base URL ──────────────────────────────────────────────────────
PORTAL_BASE_URL = "https://sunportal.com.vn"
API_BASE_URL = "https://agency-api-spa.sunportal.com.vn"

# ─── Playwright login ───────────────────────────────────────────────────────
LOGIN_URL = f"{PORTAL_BASE_URL}/login"
PLAYWRIGHT_TIMEOUT = 60_000  # ms

# Selector cho form đăng nhập (B2B Sun Portal)
AGENTCYCODE_SELECTOR = "input[name='AgencyCode']"
USERNAME_SELECTOR = "input[name='UserName']"
PASSWORD_SELECTOR = "input[name='Password']"
SUBMIT_SELECTOR = "button[type='submit']"

# ─── Tham số request mặc định ───────────────────────────────────────────────
DEFAULT_CURRENCY = "KRW"
DEFAULT_FARE_FAMILY = ["9GECO", "9GBUZ"]
DEFAULT_CHANNEL = "b2b"
