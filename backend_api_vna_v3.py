import aiohttp
import json
import re
import asyncio
import subprocess
import sys
import time

from attr import dataclass
def log_step(name, start_time):
    end = time.perf_counter()
    print(f"⏱️ {name}: {end - start_time:.3f}s")
    return end
def format_time(time_int):
    time_str = str(time_int).zfill(4)
    return f"{time_str[:2]}:{time_str[2:]}"

def parse_gia_ve(raw_str):
    parts = list(map(int, raw_str.split("/")))
    gia_goc = parts[0]
    tong_thue_phi = parts[1]
    phi_nhien_lieu = parts[2]

    return {
        "giá_vé": str(gia_goc + tong_thue_phi),
        "giá_vé_gốc": str(gia_goc),
        "phí_nhiên_liệu": str(phi_nhien_lieu),
        "thuế_phí_công_cộng": str(tong_thue_phi - phi_nhien_lieu)
    }

def format_date(ngay_str):
    if "-" in ngay_str and len(ngay_str) == 10:
        return ngay_str.replace("-", "")
    elif len(ngay_str) == 8:
        return f"{ngay_str[6:8]}/{ngay_str[4:6]}/{ngay_str[:4]}"
    else:
        
        return None

class PowerCallClient:
    def __init__(self, cookie_file="statevna.json"):
        self.cookie_file = cookie_file
        self.session = None
        self.cookies = self._load_cookies()

        self.headers = {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "accept-language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
            "sec-ch-ua": "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "referer": "https://wholesale.powercallair.com/booking/findSkdFareGroup.lts?mode=v3"
        }

        self.url = "https://wholesale.powercallair.com/booking/findSkdFareGroup.lts?viewType=xml"

    # ===== util =====
    def _load_cookies(self):
        with open(self.cookie_file, "r", encoding="utf-8") as f:
            raw = json.load(f)["cookies"]
        return {c["name"]: c["value"] for c in raw}

    def _js_object_to_json(self, text: str):
        text = re.sub(r'([{,]\s*)([A-Za-z0-9_]+)\s*:', r'\1"\2":', text)
        text = re.sub(r'([{,]\s*)(\d+)\s*:', r'\1"\2":', text)
        return json.loads(text)

    def _parse_response(self, text: str):
        text = text.strip()

        if not text:
            return "EMPTY", None

        if "<html" in text.lower():
            return "HTML", text[:300]

        if text.startswith("{") and '"' in text:
            try:
                return "JSON", json.loads(text)
            except Exception as e:
                return "JSON_ERROR", str(e)

        try:
            return "JS_OBJECT", self._js_object_to_json(text)
        except Exception as e:
            return "JS_OBJECT_ERROR", str(e)

    # ===== session =====
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(ssl=False)
        self.session = aiohttp.ClientSession(
            cookies=self.cookies,
            headers=self.headers,
            connector=connector
        )
        return self
    def relogin_vna(self):
        print("⚠️ Cookie die, gọi getcokivna.py login lại...")
        subprocess.run(
            [sys.executable, "getcokivna.py"],
            check=True
        )
    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()

    # ===== API =====
    async def getfulllistCA(
        self,
        trip: str,                 # "OW" | "RT"
        dep0: str,
        dep1: str,
        depdate0: str,             # yyyyMMdd
        depdate1: str | None = None
    ):
        is_rt = trip == "RT"

        form_data = {
            "mode": "v3",
            "qcars": "",
            "trip": trip,
            "dayInd": "N",
            "strDateSearch": depdate0[:6],
            "day": "",
            "plusDate": "",
            "daySeq": 0,

            "dep0": dep0,
            "dep1": dep1,
            "dep2": "",
            "dep3": "",

            "arr0": dep1,
            "arr1": dep0 if is_rt else "",
            "arr2": "",
            "arr3": "",

            "depdate0": depdate0,
            "depdate1": depdate1 or "",
            "depdate2": "",
            "depdate3": "",
            "retdate": depdate1 or "",

            "val": "",
            "comp": "Y",
            "adt": "1",
            "chd": "0",
            "inf": "0",
            "car": "YY",
            "idt": "ALL",
            "isBfm": "Y",
            "CBFare": "YY",
            "skipFilter": "Y",
            "miniFares": "Y",
            "sessionKey": ""
        }

        async with self.session.post(self.url, data=form_data) as resp:
            text = await resp.text()
            status, data = self._parse_response(text)

            if status == "HTML":
                self.relogin_vna()

                # reload cookie
                self.cookies = self._load_cookies()

                # tạo lại session với cookie mới
                await self.session.close()
                connector = aiohttp.TCPConnector(ssl=False)
                self.session = aiohttp.ClientSession(
                    cookies=self.cookies,
                    headers=self.headers,
                    connector=connector
                )

                # gọi lại API lần nữa
                async with self.session.post(self.url, data=form_data) as resp:
                    text = await resp.text()
                    status, data = self._parse_response(text)

                    if status != "JSON":
                        return {"status": status, "raw": data}

            elif status != "JSON":
                return {"status": status, "raw": data}

        ca_list = []
        FILTER = data.get("FILTER", {})

        for item in FILTER.get("CA", []):
            ca_list.append({
                "hang": item.get("value"),
                "ten": item.get("label"),
                "status": item.get("ST"),
                "gia_min": item.get("MA"),
                "gia_full": item.get("XA")
            })

        return {
            "status": "OK",
            "SessionKey": data.get("SessionKey"),
            "fulllist" : data
        }

    async def getflights(
        self,
        full_list: dict,
        trip: str,                 # "OW" | "RT"
        session_key: str,
        activedCar: str,
        dep0: str,
        dep1: str,
        depdate0: str,
        depdate1: str | None = None,
        activedVia: str = "0"
    ):
        is_rt = trip == "RT"

        form_data = {
            "qcars": "",
            "mode": "v3",
            "trip": trip,

            "activedCar": activedCar,
            "activedCLSS1": "Y,Q,S,B,U,K,M,Q,U,E,L,T,R,H,B,Y,S,N,V",
            "activedCLSS2": "Y,Q,S,B,U,K,M,Q,U,E,L,T,R,H,B,Y,S,N,V",
            "activedVia": activedVia,
            "activedStatus": "OK,HL",
            "activedIDT": "ADT,STU,VFR,LBR",
            "interval01Val": (
                full_list.get("FILTER", {}).get("SK", [])[0].get("IMX")
                if len(full_list.get("FILTER", {}).get("SK", [])) > 0
                else ""
            ),
            "interval02Val": (
                full_list.get("FILTER", {}).get("SK", [])[1].get("IMX")
                if len(full_list.get("FILTER", {}).get("SK", [])) > 1
                else ""
            ),
            "minAirFareView": full_list.get("FILTER", {}).get("MA", 0),
            "maxAirFareView": full_list.get("FILTER", {}).get("XA", 1000000),
            "page":     1,
            "sort": "priceAsc",

            "filterTimeSlideMin0": (
                full_list.get("FILTER", {}).get("SK", [])[0].get("DTN")
                if len(full_list.get("FILTER", {}).get("SK", [])) > 0
                else ""
            ),
            "filterTimeSlideMax0": (
                full_list.get("FILTER", {}).get("SK", [])[0].get("DTX")
                if len(full_list.get("FILTER", {}).get("SK", [])) > 0
                else ""
            ),
            "filterTimeSlideMin1": (
                full_list.get("FILTER", {}).get("SK", [])[1].get("DTN")
                if len(full_list.get("FILTER", {}).get("SK", [])) > 1
                else ""
            ),
            "filterTimeSlideMax1": (
                full_list.get("FILTER", {}).get("SK", [])[1].get("DTX")
                if len(full_list.get("FILTER", {}).get("SK", [])) > 1
                else ""
            ),

            "dayInd": "N",
            "strDateSearch": depdate0[:6],
            "daySeq": "0",
            "day" : "",
            "plusDate":"",
            "dep0": dep0,
            "dep1": dep1,
            "dep2": "",
            "dep3": "",
            "val" : "",
            "skipFilter":"",

            "arr0": dep1,
            "arr1": dep0 if is_rt else "",
            "arr2": "",
            "arr3": "",

            "depdate0": depdate0,
            "depdate1": depdate1 or "",
            "depdate2": "",
            "depdate3": "",
            "retdate": depdate1 or "",

            "comp": "Y",
            "adt": "1",
            "chd": "0",
            "inf": "0",
            "car": "YY",
            "idt": "ALL",
            "isBfm": "Y",
            "CBFare": "YY",
            "miniFares": "Y",
            "sessionKey": session_key
        }
        #print(form_data)
        # activedAirport
        form_data["activedAirport"] = (
            f"{dep0}-{dep1}-{dep1}-{dep0}" if is_rt else f"{dep0}-{dep1}"
        )

        async with self.session.post(self.url, data=form_data) as resp:
            text = await resp.text()
            status, data = self._parse_response(text)

            if status not in ("JSON", "JS_OBJECT"):
                return {"status": status, "raw": data}

        return {
            "status": "OK",
            "PAGE": data.get("PAGE"),
            "TOTALPAGE": data.get("TOTALPAGE"),
            "TOTALFARES": data.get("TOTALFARES"),
            "FARES": data.get("FARES", []),
            "SessionKey": data.get("SessionKey")
        }
def prase_flights(data,trip):
    result = []
    #print(data)
    if trip == "OW":
        for item in data:
            flight_info = { 
                "chiều_đi":{
                
                    "hãng": "VNA" if item.get("CA") == "VN" else item.get("CA"),
                    "id": item["I"],
                    "nơi_đi": item["SK"][0]["DA"],
                    "nơi_đến": item["SK"][0]["AA"],
                    "giờ_cất_cánh": format_time(int(item["SK"][0]["DT"])),
                    "ngày_cất_cánh": format_date(str(item["SK"][0]["DD"])),
                    "thời_gian_bay": str(item["SK"][0]["TT"]),
                    "thời_gian_chờ": format_time(int(item["SK"][0].get("HTX") or 0)),
                    "giờ_hạ_cánh": format_time(int(item["SK"][0]["AT"])),
                    "ngày_hạ_cánh": format_date(str(item["SK"][0]["AD"])),
                    
                    
                    "số_điểm_dừng": str(item["SK"][0]["VA"]),
                    "điểm_dừng_1": item["SK"][0].get("VA1", ""),
                    "điểm_dừng_2": item["SK"][0].get("VA2", ""),
                    
                    "loại_vé": item["CS"][:1]
                    
                },
                "thông_tin_chung":{
                    **parse_gia_ve(str(item["FA"][0]["FD"])),
                    "số_ghế_còn":  str(item["FA"][0]["AV"]),
                    "hành_lý_vna": item["IT"]


                }
                
                
            }
            result.append(flight_info)
    else :
        for item in data:
            flight_info = { 
                "chiều_đi":{
                
                    "hãng": "VNA" if item.get("CA") == "VN" else item.get("CA"),
                    "id": item["I"],
                    "nơi_đi": item["SK"][0]["DA"],
                    "nơi_đến": item["SK"][0]["AA"],
                    "giờ_cất_cánh": format_time(int(item["SK"][0]["DT"])),
                    "ngày_cất_cánh": format_date(str(item["SK"][0]["DD"])),
                    "thời_gian_bay": str(item["SK"][0]["TT"]),
                    "thời_gian_chờ": format_time(int(item["SK"][0].get("HTX") or 0)),
                    "giờ_hạ_cánh": format_time(int(item["SK"][0]["AT"])),
                    "ngày_hạ_cánh": format_date(str(item["SK"][0]["AD"])),
                    
                
                    "số_điểm_dừng": str(item["SK"][0]["VA"]),
                    "điểm_dừng_1": item["SK"][0].get("VA1", ""),
                    "điểm_dừng_2": item["SK"][0].get("VA2", ""),
                    
                    "loại_vé": item["CS"][:1]
                    
                },
                "chiều_về":{
                
                    "hãng": "VNA" if item.get("CA") == "VN" else item.get("CA"),
                    "id": item["I"],
                    "nơi_đi": item["SK"][1]["DA"],
                    "nơi_đến": item["SK"][1]["AA"],
                    "giờ_cất_cánh": format_time(int(item["SK"][1]["DT"])),
                    "ngày_cất_cánh": format_date(str(item["SK"][1]["DD"])),
                    "thời_gian_bay": str(item["SK"][1]["TT"]),
                    "thời_gian_chờ": format_time(int(item["SK"][1].get("HTX") or 0)),
                    "giờ_hạ_cánh": format_time(int(item["SK"][1]["AT"])),
                    "ngày_hạ_cánh": format_date(str(item["SK"][1]["AD"])),
                    
                    
                    "số_điểm_dừng": str(item["SK"][1]["VA"]),
                    "điểm_dừng_1": item["SK"][1].get("VA1", ""),
                    "điểm_dừng_2": item["SK"][1].get("VA2", ""),
                    
                    "loại_vé": item["CS"][3:4]
                    
                },
                "thông_tin_chung":{
                    **parse_gia_ve(str(item["FA"][0]["FD"])),
                    "số_ghế_còn":  str(item["FA"][0]["AV"]),
                    "hành_lý_vna": item["IT"]

                }
                
                
            }
            result.append(flight_info)    
    return result
async def api_checkve_vna_v3(trip:str="RT",
            dep0:str="",
            dep1:str="",
            depdate0:str="",
            depdate1:str="",
            activedCar:str="VN",
            activedVia:str="0"):
    t0 = time.perf_counter()
    depdate_0 = format_date(depdate0)
    if trip == "RT":
        depdate_1 = format_date(depdate1)
    else :depdate_1 = ""
    print("🚀 Bắt đầu main")
    async with PowerCallClient() as pc:
        t1 = time.perf_counter()
        ca = await pc.getfulllistCA(
            trip=trip,
            dep0=dep0,
            dep1=dep1,
            depdate0=depdate_0,
            depdate1=depdate_1
        )
        t1 = log_step("getfulllistCA", t1)
        print(ca["status"])
        ca_list = ca.get("fulllist", {})
        
        sskey = ca_list.get("SessionKey")
        print(sskey)
        # check có hãng VN không
        
       
        resultfull = []
        
        if  sskey :
            t2 = time.perf_counter()
            flightsVNA_baythang = await pc.getflights(
                full_list=ca["fulllist"],
                trip=trip,
                session_key=sskey,
                activedCar="VN",
                dep0=dep0,
                dep1=dep1,
                depdate0=depdate_0,
                depdate1=depdate_1,
                activedVia="0")
            t2 = log_step("getflights VNA bay thẳng", t2) 
               
            print("🔀 Bay thẳng:", flightsVNA_baythang["TOTALFARES"])
            resultfull.extend(prase_flights(
                data=flightsVNA_baythang["FARES"],
                trip=trip
            ))
            t3 = time.perf_counter()
            flightsVNA_noichuyen = await pc.getflights(
            full_list=ca["fulllist"],
            trip=trip,
            session_key=sskey,
            activedCar="VN",
            dep0=dep0,
            dep1=dep1,
            depdate0=depdate_0,
            depdate1=depdate_1,
            activedVia="1")
            t3 = log_step("getflights VNA nối chuyến", t3)
            print("🔀 Nối chuyến:", flightsVNA_noichuyen["TOTALFARES"])
            resultfull.extend(prase_flights(
                data=flightsVNA_noichuyen["FARES"],
                trip=trip
            ))
            t4 = time.perf_counter()
            if activedCar != "VN":
                flightsfull_noichuyen = await pc.getflights(
                full_list=ca["fulllist"],
                trip=trip,
                session_key=sskey,
                activedCar="KE,OZ,TW,7C",
                dep0=dep0,
                dep1=dep1,
                depdate0=depdate_0,
                depdate1=depdate_1,
                activedVia="0,1")
                t4 = log_step("getflights hãng khác", t4)
                print("🔀 Full chuyến hãng khác:", flightsfull_noichuyen["TOTALFARES"])
                t5 = time.perf_counter()
                result = prase_flights(
                    data=flightsfull_noichuyen["FARES"],
                    trip=trip
                )

                log_step("parse_flights", t5)
                resultfull.extend(prase_flights(
                    data=flightsfull_noichuyen["FARES"],
                    trip=trip
                ))
        log_step("TỔNG THỜI GIAN MAIN", t0)
        if sskey and resultfull :
            data_sorted = sorted(
                resultfull,
                key=lambda x: int(x["thông_tin_chung"]["giá_vé"])
            )
            print(len(resultfull))
            
            return {
            "status_code": 200,
            "trang": "1",
            "tổng_trang": "1",
            "session_key" : sskey,
            "activedVia" : "0,1",
            "body" : data_sorted
            }
        return {
            "status_code": 200,
            "trang": "1",
            "tổng_trang": "1",
            "session_key" : "null",
            "activedVia" : "0,1",
            "body" : "null"
            }
