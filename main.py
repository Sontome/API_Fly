from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend_api_vj import api_vj
from backen_api_vna import api_vna
from utils_telegram import send_mess as send_vj
from utils_telegram_vna import send_mess as send_vna
from typing import Optional
from fastapi import Query

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
    return {"message": "👋 Xin chào! API VJ và VNA đã gộp, tha hồ mà chiến!"}

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
    await send_vj(result)
    return {"message": result}

# ====================================================
# ✈ VNA ROUTES
# ====================================================
@app.get("/vna/check-ve-vna")
async def vna_api(
    dep0: str = Query(..., description="Sân bay đi, ví dụ: SGN"),
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
            await send_vna(result)
            return { "message": result}
        else:
            return { "message": "Không tìm được vé phù hợp"}

    except Exception as e:
        return {"success": False, "message": str(e)}