from supabase import create_client
import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(url, key)


def add_reprice_pnr(pnr: str, pnr_type: str):
    """
    Thêm PNR vào bảng reprice
    :param pnr: mã PNR (VD: ABC123)
    :param pnr_type: type reprice (VD: auto / manual / vj / vna ...)
    """

    data = {
        "pnr": pnr,
        "type": pnr_type,
        "status": "HOLD",           # optional, nếu có cột status
        "created_at": datetime.utcnow().isoformat()
    }

    res = supabase.table("reprice").insert(data).execute()

    if res.data:
        print(f"✅ Đã thêm PNR {pnr} | type={pnr_type}")
        return res.data[0]
    else:
        print("❌ Insert fail:", res)
        return None
add_reprice_pnr("ABC123", "VFR")        