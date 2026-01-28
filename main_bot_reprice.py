



from backendapi1a import repricePNR_v2
from backend_reprice import get_reprice_pnr,update_reprice_pnr
from utils_telegram import send_mess
import asyncio
from datetime import datetime, timedelta, timezone

def safe_fromiso(dt_str):
    if not dt_str:
        return None

    # Fix microsecond thiếu số
    if '.' in dt_str and '+' in dt_str:
        main, rest = dt_str.split('.', 1)
        micro, tz = rest.split('+', 1)
        micro = micro.ljust(6, '0')  # bù cho đủ 6 số
        dt_str = f"{main}.{micro}+{tz}"

    return datetime.fromisoformat(dt_str)


async def main_reprice():
    now = datetime.now(timezone.utc)
    await send_mess("Reprice ....")
    # Lấy danh sách HOLD
    listpnr = get_reprice_pnr(status="HOLD")
    print(f"🔥 Bắt đầu xử lý {len(listpnr)} PNR HOLD")

    for item in listpnr:
        try:
            pnr_id = item["id"]
            pnr = item["pnr"]
            pnr_type = item["type"]
            created_at = safe_fromiso(item["created_at"])

            # ===============================
            # 1️⃣ Quá 48h → OVERTIME
            # ===============================
            if now - created_at > timedelta(hours=48):
                update_reprice_pnr(
                    pnr_id,
                    status="OVERTIME",
                    auto_reprice=False,
                    last_checked_at=now.isoformat(),
                )
                print(f"⏰ {pnr} quá 48h → OVERTIME")
                continue

            # ===============================
            # 2️⃣ Chưa quá 48h → reprice
            # ===============================
            print(f"🚀 Reprice PNR {pnr} | type={pnr_type}")
            body = await repricePNR_v2(pnr, pnr_type)

            if not body or "status" not in body:
                print(f"⚠️ Body trả về cc gì đó cho {pnr}")
                update_reprice_pnr(
                    pnr_id,
                    last_checked_at=now.isoformat()
                )
                continue

            status = body.get("status")
            et = body.get("ET", False)
            pricegoc = body.get("pricegoc")
            pricemoi = body.get("pricemoi")

            # ===============================
            # ISSUED → PAID
            # ===============================
            if status == "ISSUED":
                update_reprice_pnr(
                    pnr_id,
                    status="PAID",
                    auto_reprice=False,
                    last_checked_at=now.isoformat(),
                )
                print(f"💰 {pnr} ISSUED → PAID")

            # ===============================
            # CANCEL
            # ===============================
            elif status == "CANCEL":
                update_reprice_pnr(
                    pnr_id,
                    status="CANCEL",
                    auto_reprice=False,
                    last_checked_at=now.isoformat(),
                )
                print(f"❌ {pnr} CANCEL")
            # ===============================
            # HL + ET → Vào được chỗ
            # ===============================
            elif status == "HL" and et is True:
                update_reprice_pnr(
                    pnr_id,
                    last_checked_at=now.isoformat(),
                )
                mess = f"PNR {pnr} đã vào được chỗ thành công"
                await send_mess(mess)
                print(f"🎯 {pnr} HL + ET → vào được chỗ")
            # ===============================
            # OK
            # ===============================
            elif status == "OK":
                fields = {
                    "last_checked_at": now.isoformat(),
                }

                if et is True:
                    fields["updated_at"] = now.isoformat()
                    fields["new_price"] = pricemoi

                if item["old_price"] is None and pricegoc is not None:
                    fields["old_price"] = pricegoc

                update_reprice_pnr(pnr_id, **fields)
                print(f"✅ {pnr} OK | ET={et}")
                # 🔔 Gửi tin nhắn khi có giảm giá
                if et is True and pricegoc and pricemoi:
                    mess = f"PNR {pnr} đã giảm giá {pricegoc} > {pricemoi}"
                    await send_mess(mess)
            # ===============================
            # Status khác OK / CANCEL
            # ===============================
            else:
                update_reprice_pnr(
                    pnr_id,
                    last_checked_at=now.isoformat()
                )
                print(f"🤷 {pnr} status={status} → chỉ update last_checked_at")

        except Exception as e:
            print(f"💥 Lỗi khi xử lý {item.get('pnr')}:", e)
    await send_mess("Đã Reprice Xong")
asyncio.run(main_reprice())
