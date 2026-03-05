from datetime import datetime, timezone, timedelta
from backend_supabase_kakao import update_sent_phone,get_unsent_latest_kakao,update_row_sent
from getinfopnr_vj import checkpnr_vj
from backend_api_kakao import send_bms_image
from backendapi1a import checkmatvechoVNA
import asyncio
KST = timezone(timedelta(hours=9))  # GMT+9


async def process_all_unsent_kakao():
    # Lấy danh sách chưa gửi
    records = get_unsent_latest_kakao()

    if not records:
        print("Không có dữ liệu cần gửi.")
        return

    for item in records:
        phone = item.get("phone")
        pnr = item.get("pnr")
        type_ = item.get("type")
        id_ = item.get("id")
        wl = item.get("wl")

        if not phone or not pnr:
            print("bỏ qua nếu thiếu dữ liệu")
            continue  # bỏ qua nếu thiếu dữ liệu

        try:
            print("gửi đến kakao "+ phone +   id_)
            await process_send_kakao(pnr, type_, phone, id_,wl)
        except Exception as e:
            print(f"Lỗi khi xử lý PNR {pnr} - {phone}: {e}")
async def process_send_kakao(PNR, type, phone,id,wl):
    now = datetime.now(KST)
    current_time = now.strftime("%Hh%Mp ngày %d/%m/%Y")
    

    if type == "ISSUED":
        prefix = f"PNR {PNR} đã xuất vé thành công vào {current_time}"
    else:
        prefix = f"PNR {PNR} đã giữ chỗ thành công vào {current_time}"

    # await nè đại ca
    result_vj = await checkpnr_vj(PNR)

    if result_vj and "kakaomess" in result_vj:
        kakaomess = result_vj["kakaomess"]
        content = f"{prefix}\n\n----------------------\n{kakaomess}"

        send_bms_image(
            to_number=phone,
            image ="VJ",
            content=content
        )
        if wl == False:
            update_sent_phone(phone)
        update_row_sent(id)
        return

    result_vna = await checkmatvechoVNA(PNR, "checkvecho")

    if result_vna and "kakaomess" in result_vna:
        
        kakaomess = result_vna["kakaomess"]
        if not kakaomess or not kakaomess.strip():
            print(f"Bỏ qua PNR {PNR} vì kakaomess rỗng")
            return

        content = f"{prefix}\n\n----------------------\n{kakaomess}"

        send_bms_image(
            to_number=phone,
            image ="VNA",
            content=content
        )
        if wl == False:
            update_sent_phone(phone)
        update_row_sent(id)
if __name__ == "__main__":
    asyncio.run(process_all_unsent_kakao())
