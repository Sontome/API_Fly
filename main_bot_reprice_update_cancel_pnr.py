



from backendapi1a import checkPNR
from backend_reprice import get_reprice_pnr,update_reprice_pnr

import asyncio
from datetime import datetime, timedelta, timezone
import re
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


async def main_reprice_update_cancel_pnr():
    now = datetime.now(timezone.utc)
    #await send_mess("Reprice ....")
    # Lấy danh sách HOLD
    listpnr = get_reprice_pnr(status="HOLD",auto_reprice = False)
    print(f"🔥 Bắt đầu xử lý {len(listpnr)} PNR HOLD")

    for item in listpnr:
        try:
            pnr_id = item["id"]
            pnr = item["pnr"]
            

            
            
            body = await checkPNR(pnr,"update_cancel")

            if not body :
                print(f"⚠️ Body trả về gì đó cho {pnr}")
                update_reprice_pnr(
                    pnr_id,
                    last_checked_at=now.isoformat()
                )
                continue

            result = body["model"]["output"]["crypticResponse"]["response"]
            
            # ===============================
            result_text = str(result)
            # PAID
            if "FA PAX 738" in result_text:
                status = "PAID"

            # Có chặng bay VN 123 hoặc VN1234
            elif re.search(r'\bVN\s?\d{3,4}\b', result_text):
                status = "OK"

            # Không có gì => CANCEL
            else:
                status = "CANCEL"
            # ===============================
            if status == "PAID":
                update_reprice_pnr(
                    pnr_id,
                    status="PAID",
                    auto_reprice=False,
                    last_checked_at=now.isoformat()
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
                    last_checked_at=now.isoformat()
                )
                
                print(f"❌ {pnr} CANCEL")
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
   
    await asyncio.sleep(2)
asyncio.run(main_reprice_update_cancel_pnr())
