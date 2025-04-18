import requests
import json

# Tạo session để giữ cookies
session = requests.Session()

# Load cookies từ file JSON
with open("statevna.json", "r", encoding="utf-8") as f:
    raw_cookies = json.load(f)

# Gắn cookies vô session
for cookie in raw_cookies["cookies"]:
    session.cookies.set(cookie['name'], cookie['value'], domain=cookie.get('domain'), path=cookie.get('path', '/'))
def get_cheapest_fare(data):
    fares = data.get("FARES", [])
    if not fares:
        return None  # Không có vé nào hết
    
    cheapest = min(fares, key=lambda fare: fare.get("MA", float("inf")))
    return cheapest
# URL và headers như fetch
url = "https://wholesale.powercallair.com/booking/findSkdFareGroup.lts?viewType=xml"

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
    "x-csrf-token": "",
    "x-requested-with": "XMLHttpRequest",
    "Referer": "https://wholesale.powercallair.com/booking/findSkdFareGroup.lts?mode=v3"
}

data = {
    "mode": "v3",
    "qcars": "",
    "trip": "RT",
    "dayInd": "N",
    "strDateSearch": "202504",
    "day": "",
    "plusDate": "",
    "daySeq": "0",
    "dep0": "ICN",
    "dep1": "DAD",
    "dep2": "",
    "dep3": "",
    "arr0": "DAD",
    "arr1": "ICN",
    "arr2": "",
    "arr3": "",
    "depdate0": "20250418",
    "depdate1": "20250423",
    "depdate2": "",
    "depdate3": "",
    "retdate": "20250423",
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


data1 = {
    'mode': 'v3',
    'activedCar': 'VN',
    'activedCLSS1': 'T,E,Z,I,L,H,Y,A',
    'activedCLSS2': 'Q,I,H,E,A,T,V,Y,L,R,Z',
    'activedAirport': 'ICN-HAN-HAN-ICN',
    'activedVia': '0',
    'activedStatus': 'OK,HL',
    'activedIDT': 'ADT,VFR',
    'minAirFareView': '204000',
    'maxAirFareView': '1415700',
    'page': '1',
    'sort': 'priceAsc',
    'interval01Val': '1100',
    'interval02Val': '1095',
    'filterTimeSlideMin0': '5',
    'filterTimeSlideMax0': '2355',
    'filterTimeSlideMin1': '5',
    'filterTimeSlideMax1': '2345',
    'trip': 'RT',
    'dayInd': 'N',
    'strDateSearch': '202504',
    'daySeq': '0',
    'dep0': 'ICN',
    'dep1': 'HAN',
    'arr0': 'HAN',
    'arr1': 'ICN',
    'depdate0': '20250419',
    'depdate1': '20250519',
    'retdate': '20250519',
    'comp': 'Y',
    'adt': '1',
    'chd': '0',
    'inf': '0',
    'car': 'YY',
    'idt': 'ALL',
    'isBfm': 'Y',
    'CBFare': 'YY',
    'miniFares': 'Y',
    'sessionKey': '4E2ZORYZAEMUZFZKJNP9'
}
response = session.post(url, headers=headers, data=data1)

# In kết quả
print("Status code:", response.status_code)
result = response.text

#result= result.get("FARES",{})
data = json.loads(result)
print("hàng")
print(data.get("PAGESIZE"))
print("trang")
print(data.get("TOTALPAGE"))
cheapest_fare = get_cheapest_fare(data)
renhat = cheapest_fare.get("XA")
if cheapest_fare:
    print("Vé rẻ nhất nè đại ca:")
    print(cheapest_fare.get("AP"))
    print(cheapest_fare.get("SK")[0].get("DD"))
    print(cheapest_fare.get("SK")[1].get("DD"))
    print(renhat)
else:
    print("Đéo thấy vé nào luôn á :))")
