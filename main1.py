from fastapi import FastAPI, Query
from backend_api_vj import api_vj  # Đảm bảo cái này là async nha
from utils_telegram import send_mess
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
# Thêm middleware CORS cho phép truy cập từ domain khác
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Hoặc thêm domain của bạn nếu cần bảo mật, ví dụ: ["https://yourwebsite.com"]
    allow_credentials=True,
    allow_methods=["*"],  # Cho phép tất cả các phương thức HTTP
    allow_headers=["*"],  # Cho phép tất cả header
)
@app.get("/")
async def hello():
    return {"message": "👋 Xin chào , API VJ sẵn sàng, vui lòng điển đầy đủ thông tin chuyến cần tìm!"}

@app.get("/check-ve-vj")

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

    # Format tin nhắn đẹp trai
    

    await send_mess(result)

    return {"message":result}