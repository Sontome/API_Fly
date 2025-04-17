from fastapi import FastAPI, Query
from backend_api_vj import api_vj  # Đảm bảo cái này là async nha

app = FastAPI()

@app.get("/")
async def hello():
    return {"message": "👋 Xin chào đại ca, API VJ sẵn sàng chiến!"}

@app.get("/check-ve-vj")
async def check_ve_vj(
    city_pair: str = Query(...),
    departure_place: str = Query(...),
    departure_place_name: str = Query(...),
    return_place: str = Query(...),
    return_place_name: str = Query(...),
    departure_date: str = Query(...),  # format yyyy-mm-dd
    return_date: str = Query(...),
    adult_count: int = Query(1),
    child_count: int = Query(0),
    sochieu: str = Query("1")  # "1" or "2"
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
        sochieu=sochieu
    )
    return result