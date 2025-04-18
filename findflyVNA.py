import aiohttp
import json
import asyncio

async def get_vna_flight_options(
    activedVia="0",
    trip="RT",
    dep0="ICN",
    arr0="HAN",
    depdate0="20250419",
    depdate1="20250519",
    retdate="20250519"
):
    # Load cookies từ file
    with open("statevna.json", "r", encoding="utf-8") as f:
        raw_cookies = json.load(f)["cookies"]

    cookies = {cookie["name"]: cookie["value"] for cookie in raw_cookies}

    # Headers chuẩn chỉnh
    headers = {
        "accept": "application/json, text/javascript, */*; q=0.01",
        "accept-language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "x-requested-with": "XMLHttpRequest",
        "Referer": "https://wholesale.powercallair.com/booking/findSkdFareGroup.lts?mode=v3"
    }

    # Body data
    form_data = {
        'mode': 'v3',
        'activedCar': 'VN',
        'activedCLSS1': 'T,E,Z,I,L,H,Y,A',
        'activedCLSS2': 'Q,I,H,E,A,T,V,Y,L,R,Z',
        'activedAirport': f"{dep0}-{arr0}-{arr0}-{dep0}",
        'activedVia': activedVia,
        'activedStatus': 'OK,HL',
        'activedIDT': 'VFR',
        'minAirFareView': '0',
        'maxAirFareView': '1415700',
        'page': '1',
        'sort': 'priceAsc',
        'interval01Val': '1100',
        'interval02Val': '1095',
        'filterTimeSlideMin0': '5',
        'filterTimeSlideMax0': '2355',
        'filterTimeSlideMin1': '5',
        'filterTimeSlideMax1': '2345',
        'trip': trip,
        'dayInd': 'N',
        'strDateSearch': depdate0[:6],
        'daySeq': '0',
        'dep0': dep0,
        'dep1': arr0,
        'arr0': arr0,
        'arr1': dep0,
        'depdate0': depdate0,
        'depdate1': depdate1,
        'retdate': retdate,
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
    form_data1 = {
        'mode': 'v3',
        'activedCar': 'VN',
        'activedCLSS1': 'T,E,Z,I,L,H,Y,A',
        'activedCLSS2': 'Q,I,H,E,A,T,V,Y,L,R,Z',
        'activedAirport': f"{dep0}-{arr0}-{arr0}-{dep0}",
        'activedVia': "1",
        'activedStatus': 'OK,HL',
        'activedIDT': 'VFR',
        'minAirFareView': '0',
        'maxAirFareView': '1500000',
        'page': '1',
        'sort': 'priceAsc',
        'interval01Val': '1100',
        'interval02Val': '1095',
        'filterTimeSlideMin0': '5',
        'filterTimeSlideMax0': '2355',
        'filterTimeSlideMin1': '5',
        'filterTimeSlideMax1': '2345',
        'trip': trip,
        'dayInd': 'N',
        'strDateSearch': depdate0[:6],
        'daySeq': '0',
        'dep0': dep0,
        'dep1': arr0,
        'arr0': arr0,
        'arr1': dep0,
        'depdate0': depdate0,
        'depdate1': depdate1,
        'retdate': retdate,
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
    
    url = "https://wholesale.powercallair.com/booking/findSkdFareGroup.lts?viewType=xml"

    async with aiohttp.ClientSession(cookies=cookies) as session:
        async with session.post(url, headers=headers, data=form_data) as response:
            if response.status != 200:
                print("Đéo gọi được API, mã lỗi:", response.status)
                return None

            result = await response.text()
            
            try:
                data = json.loads(result)
            except json.JSONDecodeError:
                print("API trả về xàm lol, không parse được JSON")
                return None

            fares = data.get("FARES", [])
            if not fares:
                print("Hết vé bay thẳng, check nối tuyến")
                async with aiohttp.ClientSession(cookies=cookies) as session:
                    async with session.post(url, headers=headers, data=form_data1) as response:
                        if response.status != 200:
                            print("Đéo gọi được API, mã lỗi:", response.status)
                            return None

                        result = await response.text()
                        
                        try:
                            data = json.loads(result)
                            fares = data.get("FARES", [])
                            if not fares:
                                print("Hết vé chiều đi hoặc chiều về, đổi ngày bay  🥲")
                                return None
                            cheapest = min(fares, key=lambda fare: fare.get("MA", float("inf")))
                            return cheapest
                        except json.JSONDecodeError:
                            print("API trả về xàm lol, không parse được JSON")
                                        
                        


                print("Hết vé chiều đi hoặc chiều về, đổi ngày bay  🥲")
                return None

            cheapest = min(fares, key=lambda fare: fare.get("MA", float("inf")))
            return cheapest
async def main():
    result = await get_vna_flight_options(
        activedVia="1",
        trip="RT",
        dep0="ICN",
        arr0="HAN",
        depdate0="20250518",
        depdate1="20250620",
        retdate="20250620"
    )
    print("Vé rẻ nhất nè đại ca 🔥:", result)

asyncio.run(main())