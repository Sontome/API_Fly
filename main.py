from fastapi import FastAPI, HTTPException, File, UploadFile, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from backend_read_PDF_VNA_VN import reformat_VNA_VN
from backend_read_PDF_VNA_EN import reformat_VNA_EN
from backend_read_PDF_VNA_KR import reformat_VNA_KR
from backend_read_PDF_VJ import reformat_VJ
from backend_checkpayment_PDF_VJ import check_payment
from backend_read_PDF_VNA import check_ngon_ngu
import os
from fastapi.responses import FileResponse
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
from utils_telegram_vna import send_mess as send_vna
from typing import Optional
from fastapi import Query
from datetime import datetime, timedelta
import asyncio
from pydantic import BaseModel, Field
from typing import Optional
from holdbookingkeyVJ import booking
from backendapi1a import checkPNR,checksomatveVNA
TEMP_DIR = "/root/API_Fly/tmp_files"
os.makedirs(TEMP_DIR, exist_ok=True)
tomorrow = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
day_after = (datetime.today() + timedelta(days=2)).strftime("%Y-%m-%d")
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
    bookingkeychieuve: Optional[str] = Field(None, description="Booking Key chiều về (nếu có)", example="")
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
    result = await loop.run_in_executor(None, booking, ds_khach, request.bookingkey, request.sochieu,request.sanbaydi, request.bookingkeychieuve)
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
    result = await checkPNR(pnr,ssid)
    print(result)
    return result

@app.post("/process-pdf-vna/")
async def process_pdf_VNA(
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
        ngonngu = check_ngon_ngu(temp_path)
        if ngonngu == "VN":
            reformat_VNA_VN(temp_path, new_text=option,output_path=output_path)
        if ngonngu == "KR":
            reformat_VNA_KR(temp_path, new_text=option,output_path=output_path)
        if ngonngu == "EN":
            reformat_VNA_EN(temp_path, new_text=option,output_path=output_path)
        
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
@app.post("/check-payment-vj/")
async def check_payment_VJ(
    
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
        
        res=check_payment(temp_path)
        
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
@app.post("/check-so-mat-ve-vna/")
async def check_so_mat_ve_VNA(pnr,ssid):
    result = await checksomatveVNA(pnr,ssid)
    print(result)
    return result