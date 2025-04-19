from fastapi import FastAPI, Query
import uvicorn
import asyncio
from typing import Optional
from backen_api_vna import api_vna
from utils_telegram_vna import send_mess
# Giả sử mấy hàm từ code cũ import từ file khác nếu cần
#from your_module import api_vna

app = FastAPI()
@app.get("/")
async def hello():
    return {"message": "👋 Xin chào , API VNA sẵn sàng, vui lòng điển đầy đủ thông tin chuyến cần tìm!"}
@app.get("/check-ve-vna")
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
            await send_mess(result)
            return {"success": True, "data": result}
            
        else:
            return {"success": False, "message": "Không tìm được vé phù hợp"}

    except Exception as e:
        return {"success": False, "message": str(e)}
if __name__ == "__main__":
    uvicorn.run("your_script_name:app", host="0.0.0.0", port=8000, reload=True)