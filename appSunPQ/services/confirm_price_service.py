"""
appSunPQ/services/confirm_price_service.py
Service lấy GIÁ CHUẨN cho một tổ hợp itinerary cụ thể Sun Portal.

Endpoint: POST /normal/create/confirm-price

Vì sao cần: giá trả về trong /normal/search (recommendation.list_pax_pricing)
chỉ là giá GHÉP GỢI Ý theo từng route riêng lẻ (ICNHAN / HANICN). Sau khi đã
chọn ra một tổ hợp cụ thể (OW: 1 chiều, RT: 2 chiều ghép lại), cần gọi lại
confirm-price với ĐÚNG tổ hợp đó (1 lần gọi duy nhất cho cả khứ hồi) để lấy
giá chuẩn (có thể lệch chút ít so với giá gợi ý ban đầu) trước khi hiển thị/
báo giá cuối cùng cho khách.

NOTE: Dùng chung ``SearchError`` (từ ``shared.exceptions``) cho lỗi ở đây
(code="CONFIRM_PRICE_FAILED") vì confirm-price về bản chất là một bước của
luồng tìm kiếm/báo giá. Nếu về sau muốn tách riêng exception type, có thể
thêm ``ConfirmPriceError`` vào ``shared/exceptions.py`` rồi đổi lại import
bên dưới — chỉ cần sửa 1 chỗ.
"""

from __future__ import annotations

from typing import Any

from appSunPQ.constants import DEFAULT_CURRENCY
from appSunPQ.endpoints import CONFIRM_PRICE
from appSunPQ.models.confirm_price import ConfirmPriceResult, build_confirm_price_payload
from appSunPQ.session_manager import SessionManager
from shared.exceptions import SearchError
from shared.logger import LogPrefix, get_logger

logger = get_logger(LogPrefix.SEARCH)


class ConfirmPriceService:
    """
    Xác nhận giá chuẩn cho 1 tổ hợp itinerary cụ thể qua Sun Portal API.

    Endpoint: POST /normal/create/confirm-price
    """

    def __init__(self, session_manager: SessionManager) -> None:
        self._sm = session_manager

    # ── Public API ──────────────────────────────────────────────────────────

    def confirm_price(
        self,
        payload: dict[str, Any],
        override_url: str | None = None,
    ) -> ConfirmPriceResult:
        """
        Gửi payload đầy đủ đã build sẵn (xem
        ``appSunPQ.models.confirm_price.build_confirm_price_payload``).

        Returns:
            ConfirmPriceResult — quan trọng nhất là ``total_amount`` /
            ``is_valid`` để cập nhật lại giá cuối cùng.

        Raises:
            SearchError: Nếu request thất bại hoặc response success=False.
        """
        return self._post(payload, override_url)

    def confirm_price_simple(
        self,
        list_itinerary: list[dict[str, Any]],
        adult: int = 1,
        child: int = 0,
        infant: int = 0,
        trip_type: str = "RT",
        currency: str = DEFAULT_CURRENCY,
        promo_code: str = "",
        corporate_code: str = "",
        direct_only: bool = False,
        flexible: bool = False,
        override_url: str | None = None,
    ) -> ConfirmPriceResult:
        """
        Helper build payload từ tham số rời rồi gọi confirm_price().

        Args:
            list_itinerary: Danh sách segment ĐÚNG format confirm-price
                (trip_id gốc dạng chuỗi, segment_id đánh số liên tục toàn bộ
                itinerary — xem ``appSunPQ.models.search._build_confirm_itinerary``).
                KHÔNG dùng list_itinerary format create-booking (trip_id 1/2).
            adult/child/infant: Phải khớp với số hành khách lúc search.
            trip_type: "RT" hoặc "OW".
            currency: Mã tiền tệ.
            promo_code/corporate_code: Mã khuyến mãi / hợp đồng (nếu có).

        Returns:
            ConfirmPriceResult.
        """
        payload = build_confirm_price_payload(
            list_itinerary=list_itinerary,
            adult=adult, child=child, infant=infant,
            trip_type=trip_type, currency=currency,
            promo_code=promo_code, corporate_code=corporate_code,
            direct_only=direct_only, flexible=flexible,
        )
        return self._post(payload, override_url)

    # ── Internal ────────────────────────────────────────────────────────────

    def _post(
        self,
        payload: dict[str, Any],
        override_url: str | None,
    ) -> ConfirmPriceResult:
        url = override_url or CONFIRM_PRICE
        http = self._sm.get_http_client()
        headers = self._sm.get_headers()

        trip_ids = [seg.get("trip_id") for seg in payload.get("list_itinerary", [])]
        logger.info(f"Confirm price: trip_ids={trip_ids}")
        logger.debug(f"POST {url} payload={payload}")

        try:
            response = http.post(url, headers=headers, json=payload)
            data = response.json()
            result = ConfirmPriceResult.from_dict(data)

            if not result.success:
                raise SearchError(
                    f"Confirm price trả về success=False: {result.error}",
                    code="CONFIRM_PRICE_FAILED",
                )

            logger.info(
                f"Confirm price kết quả: total={result.total_amount} "
                f"{result.currency}, trace_id={result.trace_id}"
            )
            return result

        except SearchError:
            raise
        except Exception as e:
            logger.exception(f"Confirm price thất bại: {e}")
            raise SearchError(
                f"Confirm price thất bại: {e}", code="CONFIRM_PRICE_FAILED"
            ) from e
