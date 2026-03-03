from datetime import datetime
from backend_supabase_kakao import update_sent_phone,get_unsent_latest_kakao
from getinfopnr_vj import checkpnr_vj
from backend_api_kakao import send_bms_image
from backendapi1a import checkmatvechoVNA
import asyncio

async def process_send_kakao(PNR, type, phone):
    current_time = datetime.now().strftime("%Hh%Mp ngày %d/%m/%Y")

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
            image_id="VJ",
            content=content
        )
        update_sent_phone(phone)
        return

    result_vna = await checkmatvechoVNA(PNR, "checkvecho")

    if result_vna and "kakaomess" in result_vna:
        kakaomess = result_vna["kakaomess"]
        content = f"{prefix}\n\n----------------------\n{kakaomess}"

        send_bms_image(
            to_number=phone,
            image_id="VNA",
            content=content
        )
        update_sent_phone(phone)
if __name__ == "__main__":
    asyncio.run(process_send_kakao("D422P2", "ISSUED", "0764301092"))
    asyncio.run(process_send_kakao("G49B3G", "HOLD", "0764301092"))
