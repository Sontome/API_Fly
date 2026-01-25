from supabase import create_client
import os
from datetime import datetime
from dotenv import load_dotenv



from datetime import datetime
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

def get_reprice_pnr(pnr: str = None, pnr_type: str = None, status: str = None):
    """
    Lấy dữ liệu từ bảng reprice
    :param pnr: lọc theo mã PNR (optional)
    :param pnr_type: lọc theo type (optional)
    :param status: lọc theo status (optional)
    """

    query = supabase.table("reprice").select("*")

    if pnr:
        query = query.eq("pnr", pnr)

    if pnr_type:
        query = query.eq("type", pnr_type)

    if status:
        query = query.eq("status", status)

    res = query.execute()

    if res.data:
        print(f"✅ Lấy được {len(res.data)} bản ghi")
        print(res.data)
        return res.data
    else:
        print("⚠️ Không có dữ liệu hoặc query fail cc gì đó:", res)
        return []
def update_reprice_pnr(
    pnr_id: str,
    **fields
):
    """
    Update dữ liệu bảng reprice theo id
    :param pnr_id: id UUID của dòng cần update
    :param fields: các cột cần update (status, old_price, new_price, last_checked_at, auto_reprice, ...)
    """

    if not fields:
        print("❌ Không có field nào để update, xàm vl")
        return None

    # auto cập nhật updated_at
    fields["updated_at"] = datetime.utcnow().isoformat()

    res = (
        supabase
        .table("reprice")
        .update(fields)
        .eq("id", pnr_id)
        .execute()
    )

    if res.data:
        print(f"✅ Update thành công PNR id={pnr_id}")
        return res.data[0]
    else:
        print("❌ Update fail cc gì đó:", res)
        return None
