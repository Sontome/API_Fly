"""
api/change_api.py
VietjetChangeAPI — raw API call layer.

Responsibilities:
- Make HTTP calls via VietjetSession
- Return (raw_response, extracted_key_fields)
- NO business logic
- NO flow orchestration
- Parser detail left as TODO stubs

All endpoints: agentapi.vietjetair.com/api/v14/EditBooking/...
"""
from urllib.parse import quote
import logging
from typing import Any

from core.exceptions import ApiResponseError
from core.session import VietjetSession
logging.getLogger("httpcore").disabled = True
logging.getLogger("httpx").disabled = True
logger = logging.getLogger(__name__)

BASE_URL = "https://agentapi.vietjetair.com/api/v14/EditBooking"



AIRPORT_NAME_MAP = {
    "ADA": "Adana Airport",
    "ADL": "Adelaide",
    "AKJ": "Hokkaido",
    "ALA": "Almaty International Airport",
    "AMD": "Ahmedabad-Sardar Vallabhbhai Patel",
    "ANC": "Ted Stevens Anchorage International Airport",
    "AOJ": "Aomori Airport",
    "ATH": "Eleftherios Venizelos International Airport",
    "ATQ": "Amritsar",
    "BAV": "Baotou",
    "BAX": "Barnaul",
    "BER": "Berlin",
    "BFI": "King County International Airport",
    "BFV": "Buri Ram",
    "BKK": "BangKok - Suvarnabhumi",
    "BLR": "Bangalore",
    "BMV": "Buon Ma Thuot",
    "BNE": "Brisbane",
    "BOM": "Mumbai",
    "BQS": "Blagoveshchensk",
    "BTH": "Hang Nadim",
    "BTZ": "Betong Airport",
    "BWA": "Nepal",
    "BWN": "Brunei International Airport",
    "CAN": "GuangZhou",
    "CCU": "Netaji Subhash Chandra Bose - Kolkata",
    "CDG": "Paris",
    "CEB": "Lapu-Lapu",
    "CEI": "Chiang Rai",
    "CGD": "Changde Taohuayuan Airport",
    "CGK": "Jakarta",
    "CGO": "Xinzheng",
    "CGQ": "Changchun",
    "CJJ": "Cheong Ju",
    "CJU": "Jeju",
    "CKG": "Chongqing",
    "CMB": "Colombo - Sri Lanka",
    "CNX": "Chiang Mai",
    "COK": "Kochi",
    "CRK": "Clark",
    "CSX": "Changsha",
    "CTS": "New Chitose",
    "CTU": "Shuangliu International Airport - Chengdu",
    "CXR": "Nha Trang",
    "CZX": "Changzhou",
    "DAC": "Hazrat Shahjalal International Airport",
    "DAD": "Da Nang",
    "DAT": "Datong Yungang",
    "DEL": "New Delhi",
    "DIN": "Dien Bien",
    "DLC": "Zhoushuizi",
    "DLI": "Da Lat",
    "DPS": "Ngurah Rai - Bali",
    "DSN": "Dongsheng",
    "DVO": "Davao",
    "DXB": "Dubai International Airport",
    "DYG": "Zhangjiajie Hehua",
    "ENH": "Enshi Xujiaping Airport",
    "FCO": "Rome",
    "FKS": "Fukushima",
    "FOC": "Changle",
    "FSZ": "Shizuoka",
    "FUK": "Fukuoka Airport",
    "GAY": "Gaya",
    "HAK": "Meilan",
    "HAN": "Ha Noi",
    "HDY": "Hat Yai International Airport",
    "HET": "Baita",
    "HFE": "Hefei Xinqiao",
    "HGH": "Hangzhou",
    "HIA": "Huai an Lianshui",
    "HIJ": "Hiroshima Airport",
    "HKG": "Hong Kong",
    "HKT": "Phuket",
    "HNA": "Hanamaki Airport",
    "HND": "Tokyo - Haneda",
    "HPH": "Hai Phong",
    "HRB": "Harbin Taiping International Airport",
    "HSG": "Saga Airport",
    "HUI": "Hue",
    "HUN": "Hualien",
    "HYD": "Hyderabad",
    "IBR": "Ibaraki",
    "ICN": "Seoul",
    "IKT": "Irkutsk",
    "INC": "Hedong",
    "JAI": "Jaipur",
    "JJN": "Jinjiang",
    "KBV": "Krabi",
    "KCZ": "Kochi - Japan",
    "KHH": "Kaohsiung",
    "KHN": "Nanchang",
    "KHV": "Khabarovsk",
    "KIJ": "Niigata",
    "KIX": "Osaka",
    "KJA": "Yemelyanovo International Airport",
    "KKC": "Khon Kaen",
    "KMG": "Kunming",
    "KMQ": "Komatsu",
    "KNH": "Kinmen",
    "KOJ": "Kagoshima Airport",
    "KOS": "Sihanoukville International Airport",
    "KTI": "Phnom Penh - Cambodia",
    "KUL": "Kuala Lumpur",
    "KWE": "Guiyang",
    "KWL": "Guilin",
    "KZN": "Kazan Airport",
    "LAO": "Laoag",
    "LHR": "London",
    "LHW": "Lanzhou Zhongchuan",
    "LIG": "Limoges",
    "LJG": "Lijiang Sanyi Airport",
    "LKO": "Lucknow",
    "LPQ": "Luang Prabang International Airport",
    "LTH": "Long Thanh",
    "LYI": "Shubuling",
    "MAA": "Chennai International Airport",
    "MEL": "Melbourne",
    "MFM": "Macau",
    "MIA": "Miami International Airport",
    "MNL": "Manila",
    "MWX": "Muan",
    "MYJ": "Matsuyama",
    "MZG": "Penghu",
    "NGB": "Ningbo",
    "NGO": "Nagoya",
    "NKG": "Nanjing Lukou",
    "NNG": "Nanning",
    "NOZ": "Novokuznetsk",
    "NQZ": "Nursultan Nazarbayev International Airport",
    "NRT": "Tokyo - Narita",
    "NST": "Nakhon Si Thammarat",
    "NTG": "Xingdong",
    "OKA": "Okinawa",
    "OKJ": "Okayama Airport",
    "ORY": "Orly",
    "OSL": "Oslo",
    "OVB": "Novosibirsk",
    "PEK": "Beijing",
    "PEN": "Penang",
    "PER": "Perth International Airport",
    "PKX": "Beijing Daxing",
    "PNH": "Phnom Penh",
    "PNQ": "Pune",
    "PQC": "Phu Quoc",
    "PRG": "Prague",
    "PUS": "Busan",
    "PVG": "Shanghai Pudong",
    "PXU": "Pleiku",
    "RGN": "Yangon",
    "RMQ": "Taichung",
    "ROR": "Koror",
    "SAI": "Siem Reap-Angkor",
    "SDJ": "Sendai Airport",
    "SGN": "Ho Chi Minh",
    "SHE": "Taoxian",
    "SHJ": "Sharjah International Airport",
    "SHM": "Shirahana",
    "SIN": "Singapore",
    "SJW": "Shijiazhuang",
    "STV": "Surat",
    "SVO": "Sheremetyevo International Airport",
    "SVX": "Ekaterinburg",
    "SWA": "Chaoshan",
    "SWF": "New York Stewart International Airport",
    "SYD": "Sydney",
    "SYX": "Sanya",
    "SZX": "Shenzhen Baoan International Airport",
    "TAE": "Daegu",
    "TAK": "Takamatsu Airport",
    "TAO": "Qingdao",
    "TAS": "Tashkent International Airport",
    "TBB": "Tuy Hoa",
    "TEN": "Songtao",
    "TFU": "Tianfu International Airport - Chengdu",
    "THD": "Thanh Hoa",
    "TNA": "Jinan",
    "TNN": "Tainan",
    "TPE": "Taipei",
    "TRZ": "Tiruchirappalli",
    "TSN": "Tianjin",
    "TTT": "Fengnin",
    "TXN": "Tunxi International Airport",
    "TYN": "Taiyuan Wusu",
    "UBN": "Mongolia",
    "UBP": "Ubon Ratchathani",
    "UFA": "Ufa",
    "UIH": "Quy Nhon",
    "UKB": "Kobe",
    "URC": "Urumqi Diwopu International Airport",
    "URT": "Surat Thani",
    "UTH": "Udon Thani",
    "UTP": "Pattaya",
    "UYN": "Yulin Yuyang Airport",
    "VCA": "Can Tho",
    "VCL": "Chu Lai",
    "VCS": "Con Dao",
    "VDH": "Dong Hoi",
    "VDO": "Van Don",
    "VII": "Vinh",
    "VKO": "Vnukovo International Airport",
    "VNS": "Varanasi",
    "VTE": "Wattay International Airport",
    "VVO": "Vladivostok",
    "WAW": "Frédéric Chopin International Airport",
    "WNZ": "Wenzhou International Airport",
    "WUH": "Wuhan",
    "WUX": "Wuxi",
    "XFN": "Xiangyang",
    "XFW": "Hamburg",
    "XIY": "Xian",
    "XMN": "Gaoqi",
    "XNN": "Xining Caojiabao Airport",
    "XUZ": "Xuzhou Guanyin",
    "XXX": "No operate",
    "YCU": "Yuncheng Guangong Airport",
    "YGJ": "Yonago",
    "YIH": "Yichang",
    "YIW": "Yiwu",
    "YNT": "Penglai",
    "YNY": "Yangyang",
    "YTY": "Taizhou Airport",
    "ZHA": "Zhanjiang",
    "ZYI": "Xinzhou"
}
def find_flight(raw, new_flight_no):
    for travel_idx, travel_option in enumerate(
        raw.get("list_Travel_Option", []), start=1
    ):
        for segment_idx, segment in enumerate(
            travel_option.get("segmentOptions", []), start=1
        ):
            flight = segment.get("flight", {})
            flight_no = flight.get("Number")

            print(
                f"[CHECK] TravelOption={travel_idx} | "
                f"Segment={segment_idx} | "
                f"Flight={flight_no}"
            )

            if flight_no == new_flight_no:
                print(
                    f"[FOUND] Flight {new_flight_no} "
                    f"ở TravelOption={travel_idx}, Segment={segment_idx}"
                   
                )

                return travel_option
                    
                

    print(f"[NOT FOUND] Không tìm thấy flight {new_flight_no}")
    return None
def count_passengers(passengers):
    adt = 0
    chd = 0
    inf = 0

    for p in passengers:
        if p.get("adult"):
            adt += 1

        if p.get("child"):
            chd += 1

        infants = p.get("infant", [])

        if isinstance(infants, list):
            inf += len(infants)

    return {
        "adt": adt,
        "chd": chd,
        "inf": inf
    }
class VietjetChangeAPI:
    """
    Thin wrapper over VietJet EditBooking API endpoints.

    Each method:
    1. Calls the endpoint via session.request()
    2. Returns raw response dict
    3. Extracts critical keys needed for next step
    4. Full parser built separately

    Args:
        session: Authenticated VietjetSession instance.
    """

    def __init__(self, session: VietjetSession):
        self._session = session

    # ------------------------------------------------------------------
    # STEP 1 — Get PNR Info
    # ------------------------------------------------------------------

    def getinfopnr(self, pnr: str) -> dict[str, Any]:
        """
        Fetch reservation detail by PNR locator.

        GET /getreservationdetailbylocator?locator={pnr}

        Args:
            pnr: Booking reference, e.g. "9TY9S6"

        Returns:
            {
                "raw_response":               dict,
                "reservation_key":            str | None,
                "old_departure_booking_key":  str | None,
                "old_return_booking_key":     str | None,
                "old_departure_journey_key":  str | None,
                "old_return_journey_key":     str | None,
                "journey_info":               dict | None,   # raw, parser TBD
            }

        Raises:
            ApiResponseError: On missing critical fields.
        """
        url = f"{BASE_URL}/getreservationdetailbylocator"
        params = {"locator": pnr}

        logger.info(f"[getinfopnr] PNR={pnr}")
        raw = self._session.get(url, params=params)
        
        # --- Extract critical keys (full parser TBD) ---
        result = self._extract_pnr_keys(raw, pnr)
        # logger.debug(f"[getinfopnr] reservation_key={result.get('reservation_key')}")
        return result
    
    def _extract_pnr_keys(self, raw: dict[str, Any], pnr: str) -> dict[str, Any]:
        """
        Extract minimal keys needed for next API steps.
        Full parser TBD — this only grabs what's needed to continue flow.

        TODO: implement full parser when API response schema is confirmed.
        """
        # ---------------------------------------------------------------
        # PARSER STUB — update keys when actual response schema is known
        # ---------------------------------------------------------------

        reservation_key = (
            raw.get("data").get("key")
            
        )

        journeys = (
            raw.get("data").get("journeys",[])
        )
        raw_passengers=(
            raw.get("data").get("passengers",[])
        )
        
        passengers= count_passengers(raw_passengers)
        
        
        return {
            "raw_response": raw,
            "reservation_key": reservation_key,
            
            "journey_info": journeys,
            "passengers":passengers
        }

    # ------------------------------------------------------------------
    # STEP 2 — Get New Trip Options
    # ------------------------------------------------------------------

    def getnewtrip(
        self,
        reservation_key: str,
        old_booking_key: str,
        dep: str,
        arr: str,
        depdate: str,
        new_flight_no: str,
        adt: int = 1,
        chd: int = 0,
        inf: int = 0,
    ) -> dict[str, Any]:
        """
        Fetch available travel options for the changed leg.

        GET /traveloption/gettraveloptionforedit?...

        Args:
            reservation_key: From getinfopnr.
            old_booking_key:  Current booking key for this leg.
            dep:              Origin IATA code (e.g. "HAN").
            arr:              Destination IATA code (e.g. "SGN").
            depdate:          New departure date "YYYY-MM-DD".
            new_flight_no:    Desired new flight number.
            adt, chd, inf:    Passenger counts.

        Returns:
            {
                "raw_response":    dict,
                "new_booking_key": str | None,
            }
        """
        url = f"{BASE_URL}/traveloption/gettraveloptionforedit"
        params = {
            "cityPair":dep+"-"+arr,
            
            "departurePlace": dep,
            "departurePlaceName": (AIRPORT_NAME_MAP.get(dep, dep)),
            "returnPlace":arr,
            "returnPlaceName": (AIRPORT_NAME_MAP.get(arr, arr)),
            "departure": depdate,
            "reservation": (reservation_key),
            "journey": (old_booking_key),
            # "flightNo": new_flight_no,
            "adultCount": str(adt),
            "childCount": str(chd),
            "infantCount": str(inf),
            "currency":"KRW",
            "promoCode":"",

        }
        print(params)
        logger.info(
            f"[getnewtrip] {dep}→{arr} on {depdate} | "
            f"flight={new_flight_no} | reservationKey={reservation_key}"
        )
        raw = self._session.get(url, params=params)
        # print(raw["data"])
        newseg = find_flight(raw["data"], new_flight_no)
        # print(newseg)
        

        return newseg

    def _extract_new_booking_key(self, raw: dict[str, Any]) -> str | None:
        """
        Extract new_booking_key from getnewtrip response.
        TODO: implement full parser when schema confirmed.
        """
        return (
            raw.get("newBookingKey")
            or raw.get("bookingKey")
            or raw.get("data", {}).get("bookingKey")
        )

    # ------------------------------------------------------------------
    # STEP 3 — Get Payment Key
    # ------------------------------------------------------------------

    def getpaymentkey(
        self,
        reservation_key: str,
        new_booking_key: str,
    ) -> dict[str, Any]:
        """
        Fetch available payment methods and retrieve payment key.

        GET /paymentMethods?reservationKey=...&bookingKey=...

        Args:
            reservation_key: From getinfopnr.
            new_booking_key:  From getnewtrip.

        Returns:
            {
                "raw_response": dict,
                "payment_key":  str | None,
            }
        """
        url = f"{BASE_URL}/paymentMethods"
        params = {
            "reservationKey": reservation_key,
            "bookingKey": new_booking_key,
            "isChangeJourney": "true"
        }

        # logger.info(
        #     f"[getpaymentkey] reservationKey={reservation_key} | "
        #     f"newBookingKey={new_booking_key}"
        # )
        raw = self._session.get(url, params=params)

        payment_key = self._extract_payment_key(raw)
        # logger.debug(f"[getpaymentkey] payment_key={payment_key}")

        return {
            "raw_response": raw,
            "payment_key": payment_key,
        }

    def _extract_payment_key(self, raw: dict[str, Any]) -> str | None:
        """
        Extract payment_key from getpaymentkey response.
        TODO: implement full parser when schema confirmed.
        """
        data0 = raw.get("data", [])

        paykey = None

        for item in data0:
            print(
                f"Payment: {item.get('identifier')} - "
                f"{item.get('paymentdescription')}"
            )

            if item.get("identifier") == "AG" and item.get("paymentdescription") == "Agency Credit":
                paykey = item.get("key")
                print("✅ Found Agency Credit key")
                break

        if not paykey:
            print("❌ Không tìm thấy payment method identifier='AG'")
        return (
            paykey
            or None
        )

    # ------------------------------------------------------------------
    # STEP 4 — Get New Price (Quotation)
    # ------------------------------------------------------------------

    def getnewprice(
        self,
        reservation_key: str,
        old_journey_key: str,
        new_booking_key: str,
        payment_key: str,
        is_gpay_international: bool = False,
    ) -> dict[str, Any]:
        """
        Request a price quotation for the journey change.
        This is a READ-ONLY quote — does NOT confirm any change.

        POST /traveloption/changeJourney/Quotation

        Args:
            reservation_key:       From getinfopnr.
            old_journey_key:       Original journey key for this leg.
            new_booking_key:       From getnewtrip.
            payment_key:           From getpaymentkey.
            is_gpay_international: GPay flag (default False).

        Returns:
            {
                "raw_response":       dict,
                "total_price_change": float | None,
                "change_fee":         float | None,
                "fare_difference":    float | None,
            }
        """
        url = f"{BASE_URL}/traveloption/changeJourney/Quotation"
        body = {
            "reservationKey": reservation_key,
            "journeyKey": old_journey_key,
            "newBookingKey": new_booking_key,
            "paymentTransactions": [
                {
                    "allPassengers": True,
                    "paymentMethod": {
                        "key": payment_key,
                        "identifier": "AG"
                    },
                    "currencyAmounts": [
                        {
                            "totalAmount": 0,
                            "exchangeRate": 0,
                            "currency": {
                                "code": "KRW",
                                "description": "KRW",
                                "baseCurrency": False
                            }
                        }
                    ]
                }
            ],
            "isGpayInternational": False
        }

        # logger.info(
        #     f"[getnewprice] reservationKey={reservation_key} | "
        #     f"journeyKey={old_journey_key} | newBookingKey={new_booking_key}"
        # )
        raw = self._session.post(url, json=body)

        pricing = self._extract_pricing(raw["data"])
        # logger.debug(f"[getnewprice] pricing={pricing}")

        return pricing

    def _extract_pricing(self, raw: dict[str, Any]) -> dict[str, Any]:
        """
        Extract pricing fields from getnewprice response.
        TODO: implement full parser when schema confirmed.
        Returns zeros as safe defaults until parser is built.
        """
        data = raw.get("payment") or raw

        return {
            "total_price_change": (
                data.get("totalExchangePayment")
                
            ),
            "change_fee": (
                data.get("totalFee")
                
            ),
            "fare_difference": (
                data.get("newLegCharge")
                
            ),
            "reservationCredits": (
                data.get("reservationCredits")
                
            )
        }
