import requests
import json
from urllib.parse import parse_qs, unquote
from urllib.parse import urlencode, quote

def dict_to_query_string(params: dict) -> str:
    """
    Chuyển dict thành query string, tự động encode giá trị.
    """
    return urlencode(params, doseq=True, quote_via=quote)

headers = {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "accept-language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "sec-ch-ua": "\"Google Chrome\";v=\"135\", \"Not-A.Brand\";v=\"8\", \"Chromium\";v=\"135\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "x-csrf-token": "",  # điền nếu cần
    "x-requested-with": "XMLHttpRequest",
    "referer": "https://wholesale.powercallair.com/booking/findSkdFareGroup.lts?mode=v3"
}

params = {
    "mode": "v3",
    "activedCar": "KE,RS,7C,TW,VN,VJ,NX,OZ",
    "activedCLSS1": "T,E,R,I,Z,L,V,H,B,Y,A",
    "activedCLSS2": "L,A,H,R,U,T,S,W,V,B,Y,Z",
    "activedAirport": "ICN-DAD-DAD-ICN",
    "activedVia": 0,
    "activedStatus":"OK,HL",
    "activedIDT": "ADT,VFR",
    "minAirFareView": 265400,
    "maxAirFareView": 1415700,
    "page": 1,
    "sort": "priceAsc",
    "interval01Val": 1085,
    "interval02Val": 1095,
    "filterTimeSlideMin0": 615,
    "filterTimeSlideMax0": 2155,
    "filterTimeSlideMin1": 5,
    "filterTimeSlideMax1": 2345,
    "trip": "RT",
    "dayInd": "N",
    "strDateSearch": 202504,
    "day":"" ,
    "plusDate":"" ,
    "daySeq": 0,
    "dep0": "ICN",
    "dep1": "DAD",
    "dep2": "",
    "dep3": "",
    "arr0": "DAD",
    "arr1": "ICN",
    "arr2":"" ,
    "arr3": "",
    "depdate0": "20250520",
    "depdate1": "20250623",
    "depdate2": "",
    "depdate3": "",
    "retdate": "20250623",
    "val": "",
    "comp": "Y",
    "adt": 1,
    "chd": 0,
    "inf": 0,
    "car": "YY",
    "idt": "ALL",
    "isBfm": "Y",
    "CBFare": "YY",
    "skipFilter": "",
    "miniFares": "Y",
    "sessionKey": "62N0EYVKSNRN6AWUCQER"
}
# Load cookies từ file nếu cần
with open("statevna.json", "r", encoding="utf-8") as f:
    cookies_raw = json.load(f)
cookies = {c["name"]: c["value"] for c in cookies_raw["cookies"]}
data = dict_to_query_string(params)
response = requests.post(
    "https://wholesale.powercallair.com/booking/findSkdFareGroup.lts?viewType=xml",
    headers=headers,
    data="mode=v3&qcars=&trip=RT&dayInd=N&strDateSearch=202504&day=&plusDate=&daySeq=0&dep0=ICN&dep1=DAD&dep2=&dep3=&arr0=DAD&arr1=ICN&arr2=&arr3=&depdate0=20250520&depdate1=20250623&depdate2=&depdate3=&retdate=20250623&val=&comp=Y&adt=1&chd=0&inf=0&car=YY&idt=ALL&isBfm=Y&CBFare=YY&skipFilter=Y&miniFares=Y&sessionKey=",
    cookies=cookies
)

fare = response.json().get("FARES",{})

def filter_vna_tickets(fare):
    
    min = 100000000
    for item in fare:
        if item.get("CA")=="VN":    
            if int(item.get("XA")) < min:
                ticket = item
                min= int(item.get("XA"))
                
    print(ticket)
    print( fare)

danhsachvna =filter_vna_tickets(fare)

