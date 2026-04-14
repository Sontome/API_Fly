from supabase import create_client
import os
from datetime import datetime
from dotenv import load_dotenv



from datetime import datetime
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(url, key)

def update_row_sent(row_id: str):
    """
    Cập nhật row_sent = true cho dòng có id tương ứng
    :param row_id: uuid của dòng trong bảng kakanoti
    """

    res = (
        supabase
        .table("kakanoti")
        .update({"row_sent": True})
        .eq("id", row_id)
        .execute()
    )
    
    if res.data:
        print(f"✅ Đã cập nhật row_sent=true cho id={row_id}")
        return res.data[0]
    else:
        print("❌ Update fail:", res)
        return None

def add_kakao_pnr(phone: str, name: str, pnr, type="HOLD", row_sent=False, email=None):
    if isinstance(pnr, str):
        pnr = pnr.replace(" ", "")
        if len(pnr) % 6 != 0:
            print("❌ Chuỗi PNR không hợp lệ đại ca")
            return None
        pnr = [pnr[i:i+6] for i in range(0, len(pnr), 6)]

    results = []

    for code in pnr:
        try:
            data = {
                "phone": phone,
                "name": name,
                "pnr": code,
                "type": type,
                "timecreat": datetime.utcnow().isoformat(),
                "row_sent": row_sent
            }

            # 👉 email xử lý riêng
            if email:
                add_pnr_email(code, email)

            res = supabase.table("kakanoti").upsert(
                data,
                on_conflict="pnr,phone"   # 🔥 key unique
            ).execute()

            if res.data:
                print(f"✅ Upsert OK PNR {code} | name={name}")
                results.append(res.data[0])
            else:
                print(f"❌ Upsert fail PNR {code}:", res)

        except Exception as e:
            print("❌ Lỗi:", e)

    return results
def update_sent_phone(phone: str):
    """
    Thêm sdt vao bảng đã gửi sent_phone
    :phone
   
    """

    data = {
        "phone": phone,
                 
        "sent_at": datetime.utcnow().isoformat()
    }

    res = supabase.table("sent_phone").insert(data).execute()

    if res.data:
        print(f"✅ Đã thêm sdt {phone} ")
        return res.data[0]
    else:
        print("❌ Insert fail:", res)
        return None
def get_unsent_latest_kakao():
    res = supabase.rpc("get_unsent_latest_kakao").execute()
    
    if res.data:
        return res.data
    else:
        return [] 
#update_sent_phone("0764301092")
def add_pnr_email(pnr: str, email: str):
    try:
        data = {
            "pnr": pnr,
            "email": email,
            "timecreat": datetime.utcnow().isoformat()
        }

        res = supabase.table("pnr_email") \
            .upsert(data, on_conflict="pnr,email") \
            .execute()

        print(f"📧 Upsert email cho PNR {pnr}")
        return res.data

    except Exception as e:
        print("❌ Lỗi add_pnr_email:", e)
        return None  
def get_kakanoti_by_pnr(pnr: str):
    """
    Lấy dữ liệu từ bảng kakanoti theo pnr
    và phone không được null / rỗng
    + loại trùng phone
    """

    if not pnr:
        print("❌ Thiếu pnr rồi đại ca")
        return []

    query = (
        supabase
        .table("kakanoti")
        .select("*")
        .eq("pnr", pnr)
        .not_.is_("phone", None)
        .neq("phone", "")
    )

    res = query.execute()

    if not res.data:
        print("⚠️ Không có dữ liệu hoặc query fail cc gì đó:", res)
        return []

    # 🔥 lọc trùng phone
    unique_data = {}
    for row in res.data:
        phone = row.get("phone")
        if phone not in unique_data:
            unique_data[phone] = row  # giữ bản ghi đầu tiên

    result = list(unique_data.values())

    # print(f"✅ Lấy được {len(result)} bản ghi (đã loại trùng phone)")
    # print(result)

    return result
def get_phone_email_from_pnr(pnr):
    res = supabase.rpc("get_phone_email_to_pnr",
        {"pnr_input": pnr}).execute()
    
    if res.data:
        return res.data
    else:
        return [] 
def add_sent_delay_pnr(pnr: str, hang: str, phone: str = None,
                       kakao_status="pending", rcs_status="pending"):
    try:
        data = {
            "pnr": pnr,
            "hang": hang,
            "phone": phone,
            "kakao_status": kakao_status,
            "rcs_status": rcs_status,
            "timecreate": datetime.utcnow().isoformat()
        }

        res = supabase.table("sent_delay_pnr").insert(data).execute()

        if res.data:
            print(f"✅ Insert sent_delay_pnr OK | pnr={pnr} | phone={phone}")
            return res.data[0]
        else:
            print("❌ Insert fail:", res)
            return None

    except Exception as e:
        print("❌ Lỗi add_sent_delay_pnr:", e)
        return None
def update_sent_delay_pnr(row_id: str,
                         kakao_status=None,
                         rcs_status=None,
                         error_message=None):
    try:
        update_data = {
            "sent_at": datetime.utcnow().isoformat()
        }

        if kakao_status:
            update_data["kakao_status"] = kakao_status

        if rcs_status:
            update_data["rcs_status"] = rcs_status

        if error_message:
            update_data["error_message"] = error_message

        res = (
            supabase
            .table("sent_delay_pnr")
            .update(update_data)
            .eq("id", row_id)
            .execute()
        )

        if res.data:
            print(f"✅ Update sent_delay_pnr OK id={row_id}")
            return res.data[0]
        else:
            print("❌ Update fail:", res)
            return None

    except Exception as e:
        print("❌ Lỗi update_sent_delay_pnr:", e)
        return None
def log_no_data_delay(pnr: str, hang: str):
    return add_sent_delay_pnr(
        pnr=pnr,
        hang=hang,
        phone=None,
        kakao_status="no_data",
        rcs_status="no_data"
    )
