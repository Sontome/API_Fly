from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend_api_vj import api_vj
from backen_api_vna import api_vna
from backend_api_vna_v2 import api_vna_v2,api_vna_rt_v2
from utils_telegram import send_mess as send_vj
from utils_telegram_vna import send_mess as send_vna
from typing import Optional
from fastapi import Query
from datetime import datetime
import asyncio

async def safe_send_vj(result):
    try:
        await send_vj(result)
    except Exception as e:
        print(f"❌ Lỗi khi gửi Telegram VJ: {e}")

async def safe_send_vna(result):
    try:
        await send_vna(result)
    except Exception as e:
        print(f"❌ Lỗi khi gửi Telegram VNA: {e}")
app = FastAPI()

# Bật CORS full quyền
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def hello():
    return {"message": "API sẵn sàng"}

# ====================================================
# 🛩 VJ ROUTES
# ====================================================
@app.get("/vj/check-ve-vj")
async def check_ve_vj(
    city_pair: str = Query(...),
    departure_place: str = Query(""),
    departure_place_name: str = Query(""),
    return_place: str = Query(""),
    return_place_name: str = Query(""),
    departure_date: str = Query(...),
    return_date: str = Query(...),
    adult_count: int = Query(1),
    child_count: int = Query(0),
    sochieu: str = Query(2),
    name: str = Query("")
):
    result = await api_vj(
        city_pair=city_pair,
        departure_place=departure_place,
        departure_place_name=departure_place_name,
        return_place=return_place,
        return_place_name=return_place_name,
        departure_date=departure_date,
        return_date=return_date,
        adult_count=adult_count,
        child_count=child_count,
        sochieu=sochieu,
        name=name
    )
    asyncio.create_task(safe_send_vj(result))
    return {"message": result}

# ====================================================
# ✈ VNA ROUTES
# ====================================================
@app.get("/vna/check-ve-vna")
async def vna_api(
    dep0: str = Query(..., description="Sân bay đi, ví dụ: ICN"),
    arr0: str = Query(..., description="Sân bay đến, ví dụ: HAN"),
    depdate0: str = Query(..., description="Ngày đi, định dạng yyyy-MM-dd hoặc yyyyMMdd"),
    depdate1: Optional[str] = Query("", description="Ngày về (nếu có), định dạng yyyy-MM-dd"),
    name: Optional[str] = Query("khách lẻ", description="Tên người đặt"),
    sochieu: int = Query(1, description="1: Một chiều, 2: Khứ hồi")
):
    try:
        result = await api_vna(
            dep0=dep0,
            arr0=arr0,
            depdate0=depdate0,
            depdate1=depdate1,
            name=name,
            sochieu=sochieu
        )
        if result:
            asyncio.create_task(safe_send_vna(result))
            return { "message": result}
        else:
            return { "message": "Không tìm được vé phù hợp"}

    except Exception as e:
        return {"success": False, "message": str(e)}
@app.get("/vna/check-ve-v2")
async def vna_api_v2(
    dep0: str = Query(..., description="Sân bay đi, ví dụ: SGN"),
    arr0: str = Query(..., description="Sân bay đến, ví dụ: HAN"),
    depdate0: str = Query(..., description="Ngày đi, định dạng yyyy-mm-dd"),
    depdate1: Optional[str] = Query(None, description="Ngày về (nếu có), định dạng yyyy-mm-dd"),
    activedVia: str = Query("0,1,2", description="Bay thẳng = '0', dừng 1 chặng ='1', dừng 2 chặng ='2', tất cả ='0,1,2'" ),
    activedIDT: str = Query("ADT,VFR", description="việt kiều = VFR, người lớn phổ thông = ADT " ),
    adt: str = Query("1", description="Số người lớn"),
    chd: str = Query("0", description="Số trẻ em"),
    inf: str = Query("0", description="Số trẻ sơ sinh"),
    page: str = Query("1", description="Số thứ tự trang"),
    sochieu: str = Query("RT", description="OW: Một chiều, RT: Khứ hồi"),
    filterTimeSlideMin0: str = Query("5", description="Thời gian xuất phát sớm nhất chiều đi (00h05p)"),
    filterTimeSlideMax0: str = Query("2355", description="Thời gian xuất phát muộn nhất chiều đi (23h55p)"),
    filterTimeSlideMin1: str = Query("5", description="Thời gian xuất phát sớm nhất chiều về (00h05p)"),
    filterTimeSlideMax1: str = Query("2355", description="Thời gian xuất phát muộn nhất chiều về (23h55p)"),
    session_key: str = Query(None, description="session_key")
):
    try:
        depdate0_dt = datetime.strptime(depdate0, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Ngày đi sai định dạng yyyy-mm-dd")
        # Nếu RT mà không có ngày về -> gán = ngày đi
    if sochieu.upper() == "RT":
        if not depdate1:
            raise HTTPException(status_code=400, detail="Vui lòng điền ngày về")
        try:
            depdate1_dt = datetime.strptime(depdate1, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Ngày về sai định dạng yyyy-mm-dd")

        if depdate1_dt < depdate0_dt:
            raise HTTPException(
                status_code=400,
                detail="Ngày về phải sau hoặc bằng ngày đi "
            )
    try:
        if sochieu.upper()!="RT":
            result = await api_vna_v2(
                dep0=dep0,
                arr0=arr0,
                depdate0=depdate0,
                activedVia=activedVia,
                activedIDT=activedIDT,
                filterTimeSlideMin0=filterTimeSlideMin0,
                filterTimeSlideMax0=filterTimeSlideMax0,
                filterTimeSlideMin1=filterTimeSlideMin1,
                filterTimeSlideMax1=filterTimeSlideMax1,
                page=page,
                adt=adt,
                chd=chd,
                inf=inf,
                sochieu=sochieu,
                session_key=session_key
            )
        if sochieu.upper()== "RT":
            result = await api_vna_rt_v2(
                dep0=dep0,
                arr0=arr0,
                depdate0=depdate0,
                depdate1=depdate1,
                activedVia=activedVia,
                activedIDT=activedIDT,
                filterTimeSlideMin0=filterTimeSlideMin0,
                filterTimeSlideMax0=filterTimeSlideMax0,
                filterTimeSlideMin1=filterTimeSlideMin1,
                filterTimeSlideMax1=filterTimeSlideMax1,
                page=page,
                adt=adt,
                chd=chd,
                inf=inf,
                sochieu=sochieu,
                session_key=session_key
            )
        if result:
            #asyncio.create_task(safe_send_vna("status_code : 200"))
            return result
        else:
            return { "status_code": 400, "body" : "Lỗi khi lấy dữ liệu"}

    except Exception as e:
        return {"status_code": 401, "body": str(e)}
