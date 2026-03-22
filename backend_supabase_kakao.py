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
def add_kakao_pnr(phone: str, name: str,pnr: str):
    """
    Thêm PNR vào bảng kakanoti
    :phone
    :param pnr: mã PNR (VD: ABC123)
    :param name: ten
    """

    data = {
        "phone": phone,
        "name": name,
        "pnr": pnr,           # optional, nếu có cột status
        "timecreat": datetime.utcnow().isoformat()
    }

    res = supabase.table("kakanoti").insert(data).execute()

    if res.data:
        print(f"✅ Đã thêm PNR {pnr} | name={name}")
        return res.data[0]
    else:
        print("❌ Insert fail:", res)
        return None
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
  
# def get_kakanoti_by_pnr(pnr: str):
#     """
#     Lấy dữ liệu từ bảng kakanoti theo pnr
#     và phone không được null / rỗng
#     + loại trùng phone
#     """

#     if not pnr:
#         print("❌ Thiếu pnr rồi đại ca")
#         return []

#     query = (
#         supabase
#         .table("kakanoti")
#         .select("*")
#         .eq("pnr", pnr)
#         .not_.is_("phone", None)
#         .neq("phone", "")
#     )

#     res = query.execute()

#     if not res.data:
#         print("⚠️ Không có dữ liệu hoặc query fail cc gì đó:", res)
#         return []

#     # 🔥 lọc trùng phone
#     unique_data = {}
#     for row in res.data:
#         phone = row.get("phone")
#         if phone not in unique_data:
#             unique_data[phone] = row  # giữ bản ghi đầu tiên

#     result = list(unique_data.values())

#     print(f"✅ Lấy được {len(result)} bản ghi (đã loại trùng phone)")
#     print(result)

#     return result
