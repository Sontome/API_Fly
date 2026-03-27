
from fastapi import FastAPI, HTTPException, File, UploadFile, Form, BackgroundTasks,Request
from fastapi.middleware.cors import CORSMiddleware
from backend_read_PDF_VNA_VN import reformat_VNA_VN
from backend_read_PDF_VNA_EN import reformat_VNA_EN
from backend_read_PDF_VNA_KR import reformat_VNA_KR
from backend_read_PDF_VJ import reformat_VJ
from backend_api_kakao import send_bms_image,kakao_delay
from backend_checkpayment_PDF_VJ import check_payment
from backend_checkpayment_PDF_VNA import check_payment_vna
from checkdate_VJ import checkdate_VJ
from checkdate_VNA import checkdate_VNA
from backend_read_PDF_VNA import check_ngon_ngu
from get_bag_info_pnr_vj import get_bag_info_vj
from get_gmail_service import get_gmail_service
from sendmail_vj import sendmail_vj
import fitz 
import os
from dotenv import load_dotenv
import re
import json
import base64
import time
from fastapi.responses import FileResponse, Response
from backend_api_vj import api_vj
from backend_api_vj_v2 import api_vj_v2
from backend_api_vj_lowest_v2 import lay_danh_sach_ve_re_nhat
from backend_api_vj_detail_v2 import api_vj_detail_v2,api_vj_detail_rt_v2
from backend_api_vj_v2 import api_vj_rt_v2
from getinfopnr_vj import checkpnr_vj
from backen_api_vna import api_vna
from backend_api_vna_v2 import api_vna_v2,api_vna_rt_v2

from backend_api_vna_detail_v2 import api_vna_detail_v2,api_vna_detail_rt_v2
from utils_telegram import send_mess as send_vj
from utils_telegram_delay import send_mess as send_vj_delay
from utils_telegram_vna import send_mess as send_vna
from typing import Optional
from fastapi import Query
from datetime import datetime, timedelta,timezone
import asyncio
from pydantic import BaseModel, Field
from typing import Optional
from holdbookingkeyVJ import booking
from backendapi1a import checkPNR,checksomatveVNA,code1a,sendemail1a,repricePNR,beginRepricePNR,giu_ve_live_cmd,checkmatvechoVNA,huyveVNA,repricePNR_v2
import shutil
from fastapi.concurrency import run_in_threadpool
from typing import List
from ocr_gemini import ocr_then_parse
from backend_api_vna_v3 import api_checkve_vna_v3
from utils_kakao import process_all_unsent_kakao
from backend_supabase_kakao import add_kakao_pnr,get_phone_email_from_pnr
from backend_reprice import add_reprice_pnr

load_dotenv()
RATE_LIMIT_MINUTES = int(os.getenv("RATE_LIMIT_MINUTES", 3))
request_limit_cache = {}
FILES_DIR = "/var/www/files"
DOMAIN = "https://apilive.hanvietair.com"
TEMP_DIR = "/root/API_Fly/tmp_files"
os.makedirs(TEMP_DIR, exist_ok=True)
BASE_DIR = "/root/matvegoc"
os.makedirs(BASE_DIR, exist_ok=True)
F2_DIR = "/root/matvef2"
os.makedirs(F2_DIR, exist_ok=True)
tomorrow = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
day_after = (datetime.today() + timedelta(days=2)).strftime("%Y-%m-%d")
KST = timezone(timedelta(hours=9))  # GMT+9

class RepriceRequest(BaseModel):
    pnrs: str
    type: str
class RateLimitUpdate(BaseModel):
    minutes: int
class KakaoRequest(BaseModel):
    
    to_number: str
    pnr: str
    time: Optional[str]=""
    type: Optional[str]=""
    trip: Optional[str]=""
    image_link: Optional[str]="https://hanvietair.com/vi"
    hang: Optional[str]=""
    reason: Optional[str]=""
    oldtime: Optional[str]=""
    newtime: Optional[str]=""
class KakaoRequestDelay(BaseModel):
    
    
    pnr: str
    
    type: Optional[str]=""
    trip: Optional[str]=""
   
    hang: Optional[str]=""
    reason: Optional[str]=""
    oldtime: Optional[str]=""
    newtime: Optional[str]=""
class KakaoAddPNRRequest(BaseModel):
    phone: str
    name: str
    pnr: str
    type : str = "ISSUED"
    row_sent : Optional[bool] = False
    email : Optional[str] = ""
class PNRRequest(BaseModel):
    pnr: str
    banner: Optional[str] =""
class VnaCheckveRequest_V3(BaseModel):
    dep0: str ="ICN"
    arr0: str ="HAN"
    depdate0: str = tomorrow
    depdate1: Optional[str] = day_after
    activedVia: str = "0,1"
    activedCar:str = ""
    
    sochieu: str = "RT"    
class CodeRequest(BaseModel):
    code: List[str]
    ssid: str
class HanhKhach(BaseModel):
    Họ: str = Field(..., example="Nguyen")
    Tên: str = Field(..., example="An")
    Hộ_chiếu: str = Field(..., example="B12345678")
    Giới_tính: str = Field(..., example="nam")
    Quốc_tịch: str = Field(..., example="VN")

class DSKhach(BaseModel):
    người_lớn: list[HanhKhach]
    trẻ_em: Optional[list[HanhKhach]] = []
    em_bé: Optional[list[HanhKhach]] = []

class BookingRequest(BaseModel):
    ds_khach: DSKhach
    bookingkey: str = Field(..., description="Booking Key chiều đi", example="")
    sochieu: str = Field(..., description="OW (1 chiều) hoặc RT (khứ hồi)", example="OW")
    sanbaydi: Optional[str] = Field(None, description="Sân bay đi (ví dụ: ICN)", example="")
    iso: Optional[str] = Field("KR", description="Sân bay đi (ví dụ: ICN)", example="")
    exten: Optional[str] = Field("82", description="Sân bay đi (ví dụ: ICN)", example="")
    phone: Optional[str] = Field("1035463396", description="Sân bay đi (ví dụ: ICN)", example="")
    email: Optional[str] = Field("hanvietair247@gmail.com", description="Sân bay đi (ví dụ: ICN)", example="")
    bookingkeychieuve: Optional[str] = Field(None, description="Booking Key chiều về (nếu có)", example="")
    phonekakao: Optional[str] = Field("", description="phonekakao (nếu có)", example="")
    emailkakao: Optional[str] = Field("", description="email (nếu có)", example="")
class VjLowFareRequest(BaseModel):
    departure: str  = Field(..., description="Mã sân bay đi (VD: ICN)",example="ICN")
    arrival: str    = Field(..., description="Mã sân bay đến (VD: HAN)", example="HAN")
    sochieu: str   = Field(..., description="OW (1 chiều) hoặc RT (khứ hồi)", example="OW")
    departure_date: str   = Field(..., description="Ngày đi (YYYY-MM-DD)", example="YYYY-MM-DD")
    return_date: Optional[str] = Field(None, description="Ngày về (YYYY-MM-DD)",example="")
    
   
class VjdetailRequest(BaseModel):
    booking_key: str =""
    adt: str = "1"
    chd: str = "0"
    inf: str = "0"
    booking_key_arrival: Optional[str] =""
    sochieu: str = "RT"   
class VjRequest(BaseModel):
    dep0: str ="ICN"
    arr0: str ="HAN"
    depdate0: str = tomorrow
    depdate1: Optional[str] = day_after
    
    
    adt: str = "1"
    chd: str = "0"
    inf: str = "0"
   
    sochieu: str = "RT"
    
class VnaRequest(BaseModel):
    dep0: str ="ICN"
    arr0: str ="HAN"
    depdate0: str = tomorrow
    depdate1: Optional[str] = day_after
    activedVia: str = "0,1,2"
    activedIDT: str = "ADT,VFR"
    adt: str = "1"
    chd: str = "0"
    inf: str = "0"
    page: str = "1"
    sochieu: str = "RT"
    filterTimeSlideMin0: str = "5"
    filterTimeSlideMax0: str = "2355"
    filterTimeSlideMin1: str = "5"
    filterTimeSlideMax1: str = "2355"
    session_key: Optional[str] = ""
class VnadetailRequest(BaseModel):
    dep0: str ="ICN"
    arr0: str ="HAN"
    depdate0: str = tomorrow
    depdate1: Optional[str] = day_after
    activedVia: str = "0,1,2"
    activedIDT: str = "ADT,VFR"
    adt: str = "1"
    chd: str = "0"
    inf: str = "0"
    page: str = "1"
    sochieu: str = "RT"
    filterTimeSlideMin0: str = "5"
    filterTimeSlideMax0: str = "2355"
    filterTimeSlideMin1: str = "5"
    filterTimeSlideMax1: str = "2355"
    miniFares: str =""
    session_key: str = ""
    hành_lý_vna: str = ""

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
@app.middleware("http")
async def rate_limit_thuhongtour(request: Request, call_next):

    host = request.headers.get("host", "")
    path = request.url.path
    ip = request.client.host

    # chỉ limit domain thuhongtour
    if "thuhongtour.com" in host:

        if path in ["/vj/check-ve-v2", "/vna/check-ve-v2"]:

            key = f"{ip}:{path}"
            now = datetime.now()

            if key in request_limit_cache:
                last_time = request_limit_cache[key]

                if now - last_time < timedelta(minutes=RATE_LIMIT_MINUTES):
                    return Response(content="null", media_type="application/json")

            request_limit_cache[key] = now

    response = await call_next(request)
    return response
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
async def VJ(
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
async def VNA(
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
async def VNA_v2(
    dep0: str = Query(..., description="Sân bay đi, ví dụ: ICN"),
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
@app.post("/vna/check-ve-v2")
async def VNA_V2(request: VnaRequest):
    try:
        depdate0_dt = datetime.strptime(request.depdate0, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Ngày đi sai định dạng yyyy-mm-dd")

    if request.sochieu.upper() == "RT":
        if not request.depdate1:
            raise HTTPException(status_code=400, detail="Vui lòng điền ngày về")
        try:
            depdate1_dt = datetime.strptime(request.depdate1, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Ngày về sai định dạng yyyy-mm-dd")

        if depdate1_dt < depdate0_dt:
            raise HTTPException(
                status_code=400,
                detail="Ngày về phải sau hoặc bằng ngày đi "
            )

    try:
        if request.sochieu.upper() != "RT":
            result = await api_vna_v2(
                dep0=request.dep0,
                arr0=request.arr0,
                depdate0=request.depdate0,
                activedVia=request.activedVia,
                activedIDT=request.activedIDT,
                filterTimeSlideMin0=request.filterTimeSlideMin0,
                filterTimeSlideMax0=request.filterTimeSlideMax0,
                filterTimeSlideMin1=request.filterTimeSlideMin1,
                filterTimeSlideMax1=request.filterTimeSlideMax1,
                page=request.page,
                adt=request.adt,
                chd=request.chd,
                inf=request.inf,
                sochieu=request.sochieu,
                session_key=request.session_key
            )
        else:
            result = await api_vna_rt_v2(
                dep0=request.dep0,
                arr0=request.arr0,
                depdate0=request.depdate0,
                depdate1=request.depdate1,
                activedVia=request.activedVia,
                activedIDT=request.activedIDT,
                filterTimeSlideMin0=request.filterTimeSlideMin0,
                filterTimeSlideMax0=request.filterTimeSlideMax0,
                filterTimeSlideMin1=request.filterTimeSlideMin1,
                filterTimeSlideMax1=request.filterTimeSlideMax1,
                page=request.page,
                adt=request.adt,
                chd=request.chd,
                inf=request.inf,
                sochieu=request.sochieu,
                session_key=request.session_key
            )

        if result:
            return result
        else:
            return { "status_code": 400, "body" : "Lỗi khi lấy dữ liệu" }

    except Exception as e:
        return {"status_code": 401, "body": str(e)}
@app.post("/vna/detail-v2")
async def vna_detail_v2(request_detail: VnadetailRequest):
    try:
        depdate0_dt = datetime.strptime(request_detail.depdate0, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Ngày đi sai định dạng yyyy-mm-dd")

    if request_detail.sochieu.upper() == "RT":
        if not request_detail.depdate1:
            raise HTTPException(status_code=400, detail="Vui lòng điền ngày về")
        try:
            depdate1_dt = datetime.strptime(request_detail.depdate1, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Ngày về sai định dạng yyyy-mm-dd")

        if depdate1_dt < depdate0_dt:
            raise HTTPException(
                status_code=400,
                detail="Ngày về phải sau hoặc bằng ngày đi "
            )
    if request_detail.session_key == "":
            raise HTTPException(
                status_code=400,
                detail="Thiếu tham số session_key"
            )
    if request_detail.miniFares == "":
            raise HTTPException(
                status_code=400,
                detail="Thiếu số thứ tự chuyến bay cần lấy thông tin"
            )
    print(f"02{request_detail.miniFares},02{int(request_detail.miniFares)+2}")
    if request_detail.hành_lý_vna == "ADT" :
        mnfare = f"02{request_detail.miniFares},02{int(request_detail.miniFares)}"
    else:
        mnfare = f"02{request_detail.miniFares},02{int(request_detail.miniFares)+2}"
    try:
        if request_detail.sochieu.upper() != "RT":
            result = await api_vna_detail_v2(
                dep0=request_detail.dep0,
                arr0=request_detail.arr0,
                depdate0=request_detail.depdate0,
                activedVia=request_detail.activedVia,
                activedIDT=request_detail.activedIDT,
                filterTimeSlideMin0=request_detail.filterTimeSlideMin0,
                filterTimeSlideMax0=request_detail.filterTimeSlideMax0,
                filterTimeSlideMin1=request_detail.filterTimeSlideMin1,
                filterTimeSlideMax1=request_detail.filterTimeSlideMax1,
                page=request_detail.page,
                adt=request_detail.adt,
                chd=request_detail.chd,
                inf=request_detail.inf,
                sochieu=request_detail.sochieu,
                miniFares=mnfare,
                session_key=request_detail.session_key
            )
        else:
            result = await api_vna_detail_rt_v2(
                dep0=request_detail.dep0,
                arr0=request_detail.arr0,
                depdate0=request_detail.depdate0,
                depdate1=request_detail.depdate1,
                activedVia=request_detail.activedVia,
                activedIDT=request_detail.activedIDT,
                filterTimeSlideMin0=request_detail.filterTimeSlideMin0,
                filterTimeSlideMax0=request_detail.filterTimeSlideMax0,
                filterTimeSlideMin1=request_detail.filterTimeSlideMin1,
                filterTimeSlideMax1=request_detail.filterTimeSlideMax1,
                page=request_detail.page,
                adt=request_detail.adt,
                chd=request_detail.chd,
                inf=request_detail.inf,
                sochieu=request_detail.sochieu,
                miniFares=mnfare,
                session_key=request_detail.session_key
            )
        
        if result:
            return result
        else:
            return { "status_code": 400, "body" : "Lỗi khi lấy dữ liệu" }
        
    except Exception as e:
        return {"status_code": 401, "body": "session hết hạn,index vé đã thay đổi"}
@app.post("/vj/check-ve-v2")
async def VJ_V2(request: VjRequest):
    try:
        depdate0_dt = datetime.strptime(request.depdate0, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Ngày đi sai định dạng yyyy-mm-dd")

    if request.sochieu.upper() == "RT":
        if not request.depdate1:
            raise HTTPException(status_code=400, detail="Vui lòng điền ngày về")
        try:
            depdate1_dt = datetime.strptime(request.depdate1, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Ngày về sai định dạng yyyy-mm-dd")

        if depdate1_dt < depdate0_dt:
            raise HTTPException(
                status_code=400,
                detail="Ngày về phải sau hoặc bằng ngày đi "
            )
    if int(request.inf) > 2 or int(request.inf)> int(request.adt):
            raise HTTPException(
                status_code=400,
                detail="Số lượng trẻ sơ sinh không được vượt quá số lượng hành khách người lớn và tối đa là 2 "
            )  
    if int(request.adt) + int(request.chd)> 9 :
            raise HTTPException(
                status_code=400,
                detail="Tổng Số lượng hành khách người lớn + trẻ em tối đa là 9"
            )   
    try:
        if request.sochieu.upper() != "RT":
            result = await api_vj_v2(
                departure_place=request.dep0,
                return_place=request.arr0,
                departure_date=request.depdate0,
                return_date="",
                adult_count=request.adt,
                child_count=request.chd,
                infant_count=request.inf,
                sochieu=request.sochieu
                
            )
        else:
            result = await api_vj_rt_v2(
                departure_place=request.dep0,
                return_place=request.arr0,
                departure_date=request.depdate0,
                return_date=request.depdate1,
                adult_count=request.adt,
                child_count=request.chd,
                infant_count=request.inf,
                sochieu=request.sochieu
            )

        if result:
            return result
        else:
            return { "status_code": 400, "body" : "Lỗi khi lấy dữ liệu" }

    except Exception as e:
        return {"status_code": 401, "body": str(e)}
@app.post("/vj/detail-v2")
async def vj_detail_v2(request: VjdetailRequest):
    if int(request.inf) > 2 or int(request.inf)> int(request.adt):
            raise HTTPException(
                status_code=400,
                detail="Số lượng trẻ sơ sinh không được vượt quá số lượng hành khách người lớn và tối đa là 2 "
            )  
    if int(request.adt) + int(request.chd)> 9 :
            raise HTTPException(
                status_code=400,
                detail="Tổng Số lượng hành khách người lớn + trẻ em tối đa là 9"
            )
    if request.sochieu.upper() == "RT":
        if not request.booking_key_arrival:
            raise HTTPException(status_code=400, detail="chưa có bookingkey chuyến về")  
    

    try:
        if request.sochieu.upper() != "RT":
            result = await api_vj_detail_v2(
                booking_key=request.booking_key,
                adult_count=int(request.adt),
                child_count=int(request.chd),
                infant_count=int(request.inf)
                
            )
        else:
            result = await api_vj_detail_rt_v2(
                booking_key=request.booking_key,
                adult_count=int(request.adt),
                child_count=int(request.chd),
                infant_count=int(request.inf),
                booking_key_arrival=request.booking_key_arrival
            )

        if result:
            return result
        else:
            return { "status_code": 400, "body" : "Lỗi khi lấy dữ liệu" }

    except Exception as e:
        return {"status_code": 500, "body": str(e)}
@app.post("/vj/booking", summary="Tạo giữ vé", tags=[" Booking"])
async def create_booking(request: BookingRequest):
    def preprocess(khach: HanhKhach):
        return {
            "Họ": khach.Họ,
            "Tên": khach.Tên,
            "Hộ_chiếu": khach.Hộ_chiếu,
            "Giới_tính": khach.Giới_tính,
            "Quốc_tịch": khach.Quốc_tịch
        }

    ds_khach = {
        "nguoilon": [preprocess(x) for x in request.ds_khach.người_lớn],
        "treem": [preprocess(x) for x in request.ds_khach.trẻ_em],
        "embe": [preprocess(x) for x in request.ds_khach.em_bé]
    }

    # Bọc hàm sync thành bất đồng bộ
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, booking, ds_khach, request.bookingkey, request.sochieu,request.sanbaydi, request.iso,request.exten,request.phone,request.email,request.bookingkeychieuve,request.phonekakao,request.emailkakao)
    asyncio.create_task(safe_send_vj(result))
    return result
@app.post("/vj/lowfare-v2")
async def vj_lowfare_v2(request: VjLowFareRequest):
      
    
    if request.sochieu.upper() == "RT":
        if not request.return_date:
            raise HTTPException(status_code=400, detail="chưa có ngày về")  
    

    try:
        
        return_date =None
        if request.return_date:
            return_date=request.return_date
        result = await lay_danh_sach_ve_re_nhat(
            departure=request.departure,
            arrival=request.arrival,
            sochieu=request.sochieu,
            departure_date=request.departure_date,
            return_date= return_date
        )
        

        if result:
            return result
        else:
            return { "status_code": 400, "body" : "Lỗi khi lấy dữ liệu" }

    except Exception as e:
        return {"status_code": 500, "body": str(e)}
@app.post("/vj/checkpnr")
async def vj_checkpnr(pnr):
    result = await checkpnr_vj(pnr)
    
    return result
@app.post("/vna/checkpnr")
async def vna_checkpnr(pnr,ssid):
    result = await checkPNR(pnr,str(ssid))
    print(result)
    return result

@app.post("/process-pdf-vna/")
async def process_pdf_VNA(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    option: str = Form(""),
    type: int = Form(0)  # 👈 thêm tham số type, mặc định 0
):
    # Tạo đường dẫn file tạm input
    temp_path = os.path.join(TEMP_DIR, f"{file.filename}")

    # Ghi file upload vào thư mục tạm
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    # Tạo đường dẫn file output
    output_path = os.path.join(TEMP_DIR, f"output_{file.filename}")
    
    # Xử lý PDF
    try:
        ngonngu = check_ngon_ngu(temp_path)
        if ngonngu == "VN":
            reformat_VNA_VN(temp_path, new_text=option,output_path=output_path, type=type)
        if ngonngu == "KR":
            reformat_VNA_KR(temp_path, new_text=option,output_path=output_path, type=type)
        if ngonngu == "EN":
            reformat_VNA_EN(temp_path, new_text=option,output_path=output_path, type=type)
        
    except Exception as e:
        return {"error": str(e)}

    # Xóa file input ngay nếu không cần giữ
    try:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    except Exception as e:
        print(f"Lỗi xóa file input: {e}")

    # Thêm task xóa file output sau khi gửi xong
    background_tasks.add_task(
        lambda: os.path.exists(output_path) and os.remove(output_path)
    )

    # Trả file output về cho client
    return FileResponse(
        path=output_path,
        filename=file.filename,
        media_type="application/pdf"
    )

@app.post("/check-payment-vj/")
async def check_payment_VJ(
    
    file: UploadFile = File(...)
    
):
    # Tạo đường dẫn file tạm input
    # Lấy tên file gốc, bỏ path cho an toàn
    original_name = os.path.basename(file.filename)

    # Đổi Itinerary- thành VJ-
    new_name = original_name.replace("Itinerary-", "VJ-", 1)

    temp_path = os.path.join(BASE_DIR, new_name)
    

    # Ghi file upload vào thư mục tạm
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    # Tạo đường dẫn file output
    res = None
    
    # Xử lý PDF
    try:
        
        res=check_payment(temp_path)
        
    except Exception as e:
        return {"error": str(e)}

    # Xóa file input ngay nếu không cần giữ
    # try:
    #     if os.path.exists(temp_path):
    #         os.remove(temp_path)
    # except Exception as e:
    #     print(f"Lỗi xóa file input: {e}")

    # Thêm task xóa file output sau khi gửi xong
    

    # Trả file output về cho client
    return res
@app.post("/check-so-mat-ve-vna/")
async def check_so_mat_ve_VNA(pnr,ssid):
    result = await checksomatveVNA(pnr,str(ssid))
    print(result)
    return result
@app.post("/checkdate-vj/")
async def checkdate_VJ_Api(
    
    file: UploadFile = File(...)
    
):
    # Tạo đường dẫn file tạm input
    temp_path = os.path.join(TEMP_DIR, f"{file.filename}")

    # Ghi file upload vào thư mục tạm
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    # Tạo đường dẫn file output
    res = None
    
    # Xử lý PDF
    try:
        
        res=checkdate_VJ(temp_path)
        
    except Exception as e:
        return {"error": str(e)}

    # Xóa file input ngay nếu không cần giữ
    try:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    except Exception as e:
        print(f"Lỗi xóa file input: {e}")

    # Thêm task xóa file output sau khi gửi xong
    

    # Trả file output về cho client

    return res
@app.post("/checkdate-vna/")
async def checkdate_VNA_Api(
    
    file: UploadFile = File(...)
    
):
    # Tạo đường dẫn file tạm input
    temp_path = os.path.join(TEMP_DIR, f"{file.filename}")

    # Ghi file upload vào thư mục tạm
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    # Tạo đường dẫn file output
    res = None
    
    # Xử lý PDF
    try:
        
        res=checkdate_VNA(temp_path)
        
    except Exception as e:
        return {"error": str(e)}

    # Xóa file input ngay nếu không cần giữ
    try:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    except Exception as e:
        print(f"Lỗi xóa file input: {e}")

    # Thêm task xóa file output sau khi gửi xong
    

    # Trả file output về cho client


    return res

import httpx
from fastapi.responses import JSONResponse

GAS_URL = "https://script.google.com/macros/s/AKfycbyzE78UvjjLohbHiGYAmQwNyYXHvxt8GJ2p5-sI4UTXFBTnI9U6OXdyUPZA2y5tjZPMEA/exec"

@app.options("/proxy-gas")
async def proxy_gas_options():
    """Xử lý preflight request để CORS không lỗi"""
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    }
    return JSONResponse(content={}, headers=headers)

@app.api_route("/proxy-gas", methods=["GET", "POST"])
async def proxy_gas(request: Request, background_tasks: BackgroundTasks):
    method = request.method
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    }

    # Lấy body nếu có
    body = None
    if method != "GET":
        try:
            body = await request.json()
        except:
            body = None

    async def forward_request():
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                await client.request(
                    method,
                    GAS_URL,
                    json=body if method != "GET" else None,
                    headers={"Content-Type": "application/json"}
                )
        except Exception as e:
            # log lỗi thôi, ko ảnh hưởng response
            import traceback
            print("Forward request error:", str(e), traceback.format_exc())

    # Cho chạy background không chờ
    background_tasks.add_task(forward_request)

    # Trả về luôn
    return JSONResponse(
        content={"status": "success", "method": method},
        headers=cors_headers
    )




@app.post("/code1a")
async def inputcode1a(data: CodeRequest):
    try:
        
        
        result = await code1a(data.code, data.ssid)
            
        return result
    except Exception as e:
        return {"error": str(e)}
       
@app.get("/get_bag_vj")
def getbagvj(
    pnr: str = Query(..., description="pnr")
  
):
    try:
        result = get_bag_info_vj(pnr)
        
        return result
    except Exception as e:

        return (str(e))    


@app.post("/process-pdf-vj/")
async def process_pdf_VJ(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    option: str = Form("")
):
    # Tạo đường dẫn file tạm input
    temp_path = os.path.join(TEMP_DIR, f"{file.filename}")

    # Ghi file upload vào thư mục tạm
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    # Tạo đường dẫn file output
    output_path = os.path.join(TEMP_DIR, f"output_{file.filename}")
    
    # Xử lý PDF
    try:
        
        reformat_VJ(temp_path, new_text=option,output_path=output_path)
        
    except Exception as e:
        return {"error": str(e)}

    # Xóa file input ngay nếu không cần giữ
    try:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    except Exception as e:
        print(f"Lỗi xóa file input: {e}")

    # Thêm task xóa file output sau khi gửi xong
    background_tasks.add_task(
        lambda: os.path.exists(output_path) and os.remove(output_path)
    )

    # Trả file output về cho client
    return FileResponse(
        path=output_path,
        filename=file.filename,
        media_type="application/pdf"
    )
GAS_BOT_URL = "https://script.google.com/macros/s/AKfycbwSc6yTGUNAiyglQINeFFXuQWG-VxkXSPBMmCIabPmgfzv72nMzV1Cd5eeO8GvuDGMT/exec"
LAST_HISTORY_ID_FILE = "last_history_id.txt"

def read_last_history_id():
    try:
        with open(LAST_HISTORY_ID_FILE, "r") as f:
            return int(f.read().strip())
    except:
        return None

def save_last_history_id(history_id):
    with open(LAST_HISTORY_ID_FILE, "w") as f:
        f.write(str(history_id))


@app.api_route("/proxy-gas-bot", methods=["POST"], operation_id="proxy_gas_bot")
async def proxy_gas_bot(request: Request):
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    }

    try:
        body = await request.json()
        history_id = body.get("historyId")
        if not history_id:
            return JSONResponse({"status":"error","message":"No historyId"}, headers=cors_headers)

        last_history_id = read_last_history_id() or history_id

        async def delayed_request():
            try:
                service = get_gmail_service()
                # Lấy các messageAdded kể từ last_history_id
                history_resp = service.users().history().list(
                    userId="me",
                    startHistoryId=last_history_id,
                    historyTypes=["messageAdded"]
                ).execute()

                messages = []
                for h in history_resp.get("history", []):
                    if "messagesAdded" in h:
                        for m in h["messagesAdded"]:
                            messages.append(m["message"]["id"])

                # Lưu historyId mới nhất để lần sau check
                save_last_history_id(history_id)

                if messages:
                    await asyncio.sleep(5)
                    async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
                        await client.get(f"{GAS_BOT_URL}?todo=check")
            except Exception as e:
                print("🔥 Error in delayed_request:", e)

        asyncio.create_task(delayed_request())

        return JSONResponse(
            content={"status": "ok", "message": "Received Pub/Sub, checking mail in background 🚀"},
            headers=cors_headers
        )

    except Exception as e:
        import traceback
        print(str(e))
        return JSONResponse(
            content={
                "error": str(e),
                "trace": traceback.format_exc()
            },
            status_code=500,
            headers=cors_headers
        )


@app.get("/sendmailvna")
async def sendemail_1a(
    code: str = Query(..., description="code"),
    ssid: str = Query(..., description="ssidsession")
):
    try:
        result = await sendemail1a(code,ssid)
        
        return result
    except Exception as e:
        return (str(e))


@app.get("/sendmail_vj")
def sendmailvj(
    pnr: str = Query(..., description="pnr")
  
):
    try:
        result = sendmail_vj(pnr)
        
        return result
    except Exception as e:

        return (str(e))   


@app.post("/check-payment-vna/")
async def checkpaymentVNA(
    
    file: UploadFile = File(...)
    
):
    # Lấy tên file gốc, bỏ path cho an toàn
    filename = os.path.basename(file.filename)

    # Thay khoảng trắng thành _
    filename = filename.replace(" ", "_")

    # Tạo path
    temp_path = os.path.join(BASE_DIR, filename)

    # Ghi file upload vào thư mục tạm
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    # Tạo đường dẫn file output
    res = None
    
    # Xử lý PDF
    try:
        
        res=check_payment_vna(temp_path)
        
    except Exception as e:
        return {"error": str(e)}

    # Xóa file input ngay nếu không cần giữ
    # try:
    #     if os.path.exists(temp_path):
    #         os.remove(temp_path)
    # except Exception as e:
    #     print(f"Lỗi xóa file input: {e}")

    # Thêm task xóa file output sau khi gửi xong
    

    # Trả file output về cho client
    return res
@app.get("/get-pnr/{pnr}")
def get_pnr_file_png(pnr: str):
    """Trả về ảnh PNG của page 1 PDF"""
    file_path = os.path.join(FILES_DIR, f"{pnr}.pdf")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Không tìm thấy file PNR này")

    try:
        doc = fitz.open(file_path)
        page = doc[0]  # chỉ page đầu
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # scale 2x để nét hơn
        img_bytes = pix.tobytes("png")
        doc.close()
        
        return Response(content=img_bytes, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi chuyển PDF → PNG: {e}")

@app.get("/list-pnr/{pnr_key}")
def list_pnr_files(pnr_key: str):
    """Trả về danh sách link các file PDF có chứa chuỗi pnr_key"""
    if not os.path.exists(FILES_DIR):
        raise HTTPException(status_code=500, detail="Thư mục files chưa tồn tại")

    # lọc file có chứa pnr_key ở bất kỳ vị trí nào
    files = [f for f in os.listdir(FILES_DIR) if pnr_key in f and f.endswith(".pdf")]

    if not files:
        raise HTTPException(status_code=404, detail="Không tìm thấy file nào chứa chuỗi này")

    # Trả về list link đầy đủ để user tải
    links = [f"{DOMAIN}/get-pnr/{os.path.splitext(f)[0]}" for f in files]
    return {"search": pnr_key, "files": links}

@app.post("/ocr")
async def upload_image(files: List[UploadFile] = File(...)):
    results = []
    temp_files = []
    try:
        for file in files:
            temp_path = f"temp_{file.filename}"
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            temp_files.append(temp_path)

        # xử lý từng file trong threadpool (ko block event loop)
        for p in temp_files:
            result = await run_in_threadpool(ocr_then_parse, p)
            results.append({"filename": os.path.basename(p), "result": result})

        return {"count": len(results), "data": results}
    finally:
        # xóa file tạm
        for p in temp_files:
            try:
                os.remove(p)
            except Exception:
                pass


@app.get("/reprice")
async def repricee(
    pnr: str = Query(..., description="pnr"),
    doituong: str = Query(..., description="doituong")
):
    try:
        result = await repricePNR(pnr,doituong)
        
        return result
    except Exception as e:
        return (str(e))
@app.get("/reprice_v2")
async def repriceev2(
    pnr: str = Query(..., description="pnr"),
    doituong: str = Query(..., description="doituong")
):
    try:
        result = await repricePNR_v2(pnr,doituong)
        
        return result
    except Exception as e:
        return (str(e))        
@app.get("/beginReprice")
async def beginRepricee(
    pnr: str = Query(..., description="pnr")
    
):
    try:
        result = await beginRepricePNR(pnr)
        
        return result
    except Exception as e:
        return (str(e))

@app.post("/giuveVNAlive")
async def giuveVNAlive(
    hanhkhach: List[str] = Query(..., description="Danh sách hành khách, ví dụ ?hanhkhach=A&hanhkhach=B"),
    dep: str = Query(..., description="Điểm đi, ví dụ: ICN"),
    arr: str = Query(..., description="Điểm đến, ví dụ: HAN"),
    depdate: str = Query(..., description="Ngày đi, ví dụ: 20FEB"),
    deptime: str = Query(..., description="Giờ đi, ví dụ: 1035"),
    arrdate: Optional[str] = Query(None, description="Ngày đến (nếu có)"),
    arrtime: Optional[str] = Query(None, description="Giờ đến (nếu có)"),
    doituong: str = Query("VFR", description="Đối tượng giá, ví dụ: ADT/STU/VFR"),
    email: Optional[str] = Query(None, description="email F2 (nếu có)"),
    phone: Optional[str] = Query(None, description="phone F2 (nếu có)"),
    phonekakao: Optional[str] = Query("", description="phone gửi noti kakao (nếu có)"),
    emailkakao: Optional[str] = Query("", description="email gửi noti kakao (nếu có)")
    
    
):
    try:
        result = await giu_ve_live_cmd(hanhkhach=hanhkhach,
            dep=dep,
            arr=arr,
            depdate=depdate,
            deptime=deptime,
            arrdate=arrdate,
            arrtime=arrtime,
            doituong=doituong,
            email = email,
            phone= phone,
            phonekakao= phonekakao,
            emailkakao=emailkakao                           
            )
            
        
        return result
    except Exception as e:
        return (str(e))




@app.get("/checkvechoVNA")
async def checkmatvecho_VNA(
    pnr: str = Query(..., description="pnr")
    
):
    try:
        result = await checkmatvechoVNA(pnr,"checkmatvecho")
        
        return result
    except Exception as e:
        return (str(e))
@app.post("/huyveVNA")
async def huyve_VNA(
    pnr: str = Query(..., description="pnr"),
    ssid: str = Query(..., description="ssid")
    
):
    try:
        result = await huyveVNA(pnr,ssid)
        
        return result
    except Exception as e:
        return (str(e))
@app.post("/vna/check-ve-v3")
async def VNA_V3(request: VnaCheckveRequest_V3):
    try:
        depdate0_dt = datetime.strptime(request.depdate0, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Ngày đi sai định dạng yyyy-mm-dd")

    if request.sochieu.upper() == "RT":
        if not request.depdate1:
            raise HTTPException(status_code=400, detail="Vui lòng điền ngày về")
        try:
            depdate1_dt = datetime.strptime(request.depdate1, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Ngày về sai định dạng yyyy-mm-dd")

        if depdate1_dt < depdate0_dt:
            raise HTTPException(
                status_code=400,
                detail="Ngày về phải sau hoặc bằng ngày đi "
            )

    try:
        
        result = await api_checkve_vna_v3(
            dep0=request.dep0,
            dep1=request.arr0,
            depdate0=request.depdate0,
            depdate1=request.depdate1,
            activedVia=request.activedVia,
            
            trip=request.sochieu,
            activedCar=request.activedCar
        )
        

        if result:
            return result
        else:
            return { "status_code": 400, "body" : "Lỗi khi lấy dữ liệu" }

    except Exception as e:
        return {"status_code": 401, "body": str(e)}


@app.post("/list-pnr-v2")
def list_pnr_files(background_tasks: BackgroundTasks,data: PNRRequest):
    """Trả về danh sách link các file PDF có chứa chuỗi pnr_key"""
    pnr_key = data.pnr
    if not os.path.exists(BASE_DIR):
        raise HTTPException(status_code=500, detail="Thư mục files chưa tồn tại")

    # lọc file có chứa pnr_key ở bất kỳ vị trí nào
    files = [
        f for f in os.listdir(BASE_DIR)
        if (
            pnr_key in f
            and f.upper().endswith(".PDF")
            and (
                f.upper().startswith("VJ")
                or f.upper().startswith("VNA")
            )
        )
    ]

    if not files:
        raise HTTPException(status_code=404, detail="Không tìm thấy file nào chứa chuỗi này")
    for filename in files:
        input_path = os.path.join(BASE_DIR, filename)
        output_path = os.path.join(TEMP_DIR, filename)

        try:
            # ===== LUỒNG VJ =====
            if filename.upper().startswith("VJ"):
                reformat_VJ(
                    input_path,
                    new_text=data.banner,
                    output_path=output_path
                )

            # ===== LUỒNG VNA (CHƯA HOÀN THIỆN) =====
            elif filename.upper().startswith("VNA"):
                try:
                    ngonngu = check_ngon_ngu(input_path)
                    if ngonngu == "VN":
                        reformat_VNA_VN(input_path, new_text=data.banner,output_path=output_path, type=0)
                    if ngonngu == "KR":
                        reformat_VNA_KR(input_path, new_text=data.banner,output_path=output_path, type=0)
                    if ngonngu == "EN":
                        reformat_VNA_EN(input_path, new_text=data.banner,output_path=output_path, type=0)
                    
                except Exception as e:
                    return {"error": str(e)}
            
                
            
                

            else:
                continue

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Lỗi xử lý file {filename}: {str(e)}"
            )

        # Xóa file output sau khi gửi xong
        background_tasks.add_task(
            lambda p=output_path: os.path.exists(p) and os.remove(p)
        )
    # Trả về list link đầy đủ để user tải
    links = [f"{DOMAIN}/get-pnr/{os.path.splitext(f)[0]}" for f in files]
    return {"search": pnr_key, "files": links}

@app.post("/kakao-api")
def send_mess_kakao(req: KakaoRequest):
    try:
        result = send_bms_image(
            
            to_number= req.to_number,
            pnr= req.pnr,
            time= req.time,
            type= req.type,
            trip= req.trip,
            image_link= req.image_link,
            hang= req.hang,
            reason= req.reason,
            oldtime= req.oldtime,
            newtime= req.newtime
        )
        return result
    except Exception as e:
        return {"error": str(e)}
@app.post("/kakao-api-delay")
def send_mess_kakao_delay(req: KakaoRequestDelay):
    try:
        result = kakao_delay(
            
            
            pnr= req.pnr,
            
            type= req.type,
            trip= req.trip,
            
            hang= req.hang,
            reason= req.reason,
            oldtime= req.oldtime,
            newtime= req.newtime
        )
        return result
    except Exception as e:
        return {"error": str(e)}
@app.post("/kakao-add-queue")
def addkakaopnr(req: KakaoAddPNRRequest):
    try:
        result = add_kakao_pnr(
            phone=req.phone,
            name=req.name,
            pnr=req.pnr,
            type = req.type,
            row_sent = req.row_sent,
            email=req.email
        )
        return result
    except Exception as e:
        return {"error": str(e)}
@app.post("/api/kakao-trigger")
async def kakao_trigger():
    now = datetime.now(KST)

    start_time = now.replace(hour=8, minute=0, second=0, microsecond=0)
    end_time = now.replace(hour=20, minute=50, second=0, microsecond=0)

    # Nếu ngoài khung giờ thì bỏ qua
    # if not (start_time <= now <= end_time):
    #     print("Ngoài khung giờ gửi, bỏ qua.")
    #     return {"status": "outside_allowed_time"}

    await process_all_unsent_kakao()
    return {"status": "ok"}
@app.post("/admin/set-rate-limit")
async def set_rate_limit(data: RateLimitUpdate):

    global RATE_LIMIT_MINUTES
    RATE_LIMIT_MINUTES = data.minutes

    # ghi lại vào .env
    env_path = ".env"
    lines = []

    with open(env_path, "r") as f:
        lines = f.readlines()

    with open(env_path, "w") as f:
        for line in lines:
            if line.startswith("RATE_LIMIT_MINUTES="):
                f.write(f"RATE_LIMIT_MINUTES={data.minutes}\n")
            else:
                f.write(line)

    return {
        "status": "ok",
        "new_rate_limit": RATE_LIMIT_MINUTES
    }

@app.post("/add-reprice")
def add_reprice(data: RepriceRequest):
    pnrs = data.pnrs
    type = data.type
    if not pnrs:
        return {
            "success": False,
            "message": "Không có PNR hợp lệ"
        }
    result = add_reprice_pnr(pnrs = pnrs , pnr_type = type)
    return {
            "success": True,
            "message": "OK"
        }
    
async def process_events(events):
    if isinstance(events, dict):
        events = [events]

    for event in events:
        try:
            status_code = event.get("statusCode")
            kakao = event.get("kakaoOptions", {})
            template_id = kakao.get("templateId")
            print(template_id)
            type_map = {
                os.getenv("IMAGE_DELAY"): "Delay",
                os.getenv("IMAGE_VJ"): "Giữ vé",
                os.getenv("IMAGE_VJ"): "Xuất vé",
            }
            print(type_map)
            msg_type = type_map.get(template_id, "Không rõ")

            variables = kakao.get("variables", {})
            pnr = variables.get("#{pnr}", "")

            status = "thành công" if status_code == "4000" else "thất bại"
            to = event.get("to")

            content = f"Thông báo {msg_type} PNR: {pnr}\nĐã gửi kakao {status}: {to}"

            # 🔥 await async function
            if msg_type == "Delay":
                
                await send_vj_delay(content)
            else:
                await send_vj(content)

        except Exception as e:
            print("Lỗi xử lý event:", e)





@app.post("/webhook")
async def webhook(request: Request):
    events = await request.json()

    # chạy nền chuẩn async
    asyncio.create_task(process_events(events))

    return {"status": "OK"}    


@app.get("/get_phone_email")
def getphoneemail(
    pnr: str = Query(..., description="pnr")
  
):
    try:
        result = get_phone_email_from_pnr(pnr)
        
        return result
    except Exception as e:

        return None







































































