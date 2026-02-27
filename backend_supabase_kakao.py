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

    

    print(result)
