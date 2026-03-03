from supabase import create_client
import os
from datetime import datetime
from dotenv import load_dotenv



from datetime import datetime
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(url, key)


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
