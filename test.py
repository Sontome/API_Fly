import aiohttp
import json
import re
import asyncio

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

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()

    # ===== API =====
    async def getfulllistCA(self):
        form_data = {
            "mode": "v3",
            "qcars": "",
            "trip": "RT",
            "dayInd": "N",
            "strDateSearch": "202512",
            "day": "",
            "plusDate": "",
            "daySeq": "0",
            "dep0": "ICN",
            "dep1": "HAN",
            "dep2": "",
            "dep3": "",
            "arr0": "HAN",
            "arr1": "ICN",
            "arr2": "",
            "arr3": "",
            "depdate0": "20251228",
            "depdate1": "20260102",
            "depdate2": "",
            "depdate3": "",
            "retdate": "20260102",
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

            if status != "JSON":
                return {"status": status, "raw": data}

        ca_list = []
        for item in data.get("FILTER", {}).get("CA", []):
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
            "CA": ca_list
        }

    async def getflights(self, session_key: str):
        form_data = {
            "qcars": "",
            "mode": "v3",
            "activedCar": "KE,7C,VN,CZ,CA",
            "activedCLSS1": "Y,Q,S,B,U,K,M,Q,U,E,L,T,R,H,B,Y,S,N,V,",
            "activedCLSS2": "Q,U,E,L,T,R,H,B,Y,S,N,V,P",
            "activedAirport": "ICN-HAN-HAN-ICN",
            "activedVia": "0",
            "activedStatus": "OK,HL",
            "activedIDT": "ADT,STU,VFR,LBR",
            "minAirFareView": "514100",
            "maxAirFareView": "1611400",
            "page": "1",
            "sort": "priceAsc",
            "interval01Val": "1210",
            "interval02Val": "1195",
            "filterTimeSlideMin0": "1055",
            "filterTimeSlideMax0": "2120",
            "filterTimeSlideMin1": "0140",
            "filterTimeSlideMax1": "2340",
            "trip": "RT",
            "dayInd": "N",
            "strDateSearch": "202512",
            "day": "",
            "plusDate": "",
            "daySeq": "0",
            "dep0": "ICN",
            "dep1": "HAN",
            "dep2": "",
            "dep3": "",
            "arr0": "HAN",
            "arr1": "ICN",
            "arr2": "",
            "arr3": "",
            "depdate0": "20251228",
            "depdate1": "20260102",
            "depdate2": "",
            "depdate3": "",
            "retdate": "20260102",
            "val": "",
            "comp": "Y",
            "adt": "1",
            "chd": "0",
            "inf": "0",
            "car": "YY",
            "idt": "ALL",
            "isBfm": "Y",
            "CBFare": "YY",
            "skipFilter": "",
            "miniFares": "Y",
            "sessionKey": session_key
        }

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
async def main():
    async with PowerCallClient() as pc:
        ca = await pc.getfulllistCA()
        print(ca)

        sskey = ca.get("SessionKey")
        if sskey:
            flights = await pc.getflights(sskey)
            print(flights)
            print(sskey)

asyncio.run(main())