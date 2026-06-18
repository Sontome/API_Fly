from datetime import datetime
from math import e
from backendapi1a import send_command,checkmatvechoVNA
import httpx
from vna_1a.pnr_parser import SegmentParser
from vna_1a.availability_parser import AvailabilityParser
import re


def build_search_new_trip(
    dep,
    arr,
    depdate,
    deptime,
    arrdate=None,
    arrtime=None
):
    """
    Build command dạng:

    Có arrdate + arrtime:
    anvn17JULICN HAN1005*19JUL1635

    Không có:
    anvn17JULICN HAN1005
    """

    dep_dt = datetime.strptime(depdate, "%Y-%m-%d")
    dep_str = dep_dt.strftime("%d%b").upper()

    command = f"anvn{dep_str}{dep} {arr}{deptime}"

    # Nếu có đủ arrdate + arrtime thì append thêm
    if arrdate and arrtime:
        arr_dt = datetime.strptime(arrdate, "%Y-%m-%d")
        arr_str = arr_dt.strftime("%d%b").upper()

        command += f"*{arr_str}{arrtime}"

    return command

def get_price_new(raw):

    

    grd_match = re.search(
        r"GRAND TOTAL\s+KRW\s+(-?\d+)",
        raw
    )

    

    if grd_match :
        total = int(grd_match.group(1))
        
        return {
            "price": total
            
        }

    return None
def get_lowest_trip(
    groups,
    num,
    deptime,
    deptimedone,
    arrtime=None,
    arrtimedone=None
):
    """
    Return:
    SS2T1*T11

    Logic:
    - group đầu: SS đầy đủ
    - group sau: chỉ {class}{index}
    - lấy hạng thấp nhất còn đủ ghế

    Nếu có truyền arrtime/arrtimedone:
    - bắt buộc phải tìm được chiều về
    - không có chiều về => return None
    """

    # thứ tự hạng cố định
    CLASS_ORDER = [
        "F", "A", "J", "C", "D", "I",
        "W", "S",
        "Y", "B", "M", "H", "K",
        "L", "Q", "N", "R", "T", "E"
    ]

    def normalize_time(t):

        if not t:
            return None

        t = str(t).strip()

        # bỏ :
        t = t.replace(":", "")

        # HHMMSS -> HHMM
        if len(t) >= 6:
            t = t[:4]

        return t.zfill(4)

    # normalize
    deptime = normalize_time(deptime)
    deptimedone = normalize_time(deptimedone)

    arrtime = normalize_time(arrtime)
    arrtimedone = normalize_time(arrtimedone)

    ss_parts = []

    found_outbound = False
    found_inbound = False

    for i, group in enumerate(groups):

        if not group.flights:
            continue

        selected_flight = None

        for flight in group.flights:

            dep = normalize_time(
                getattr(flight, "departure_time", None)
            )

            arr = normalize_time(
                getattr(flight, "arrival_time", None)
            )

            # group đầu -> chiều đi
            if i == 0:

                if dep == deptime and arr == deptimedone:
                    selected_flight = flight
                    found_outbound = True
                    break

            # group sau -> chiều về
            else:

                if (
                    arrtime
                    and arrtimedone
                    and dep == arrtime
                    and arr == arrtimedone
                ):
                    selected_flight = flight
                    found_inbound = True
                    break

        if not selected_flight:
            continue

        booking_classes = selected_flight.booking_classes

        valid_class = None

        # duyệt từ thấp -> cao
        for cls in reversed(CLASS_ORDER):

            if cls not in booking_classes:
                continue

            seat = booking_classes[cls]

            if not str(seat).isdigit():
                continue

            if int(seat) >= num:
                valid_class = cls
                break

        if not valid_class:
            continue

        # group đầu
        if i == 0:

            ss_parts.append(
                f"SS{num}{valid_class}{selected_flight.index}"
            )

        # group sau
        else:

            ss_parts.append(
                f"{valid_class}{selected_flight.index}"
            )

    # không tìm thấy chiều đi
    if not found_outbound:
        return None

    # có yêu cầu chiều về nhưng không có
    if arrtime and arrtimedone and not found_inbound:
        return None

    return "*".join(ss_parts)

def get_newseg(segs, pax_total, doituong=""):

    seg_numbers = []

    for seg in segs:

        if getattr(seg.status, "value", "") == "FLOWN":
            continue

        seg_numbers.append(str(seg.seg_no))

    result = {
        "cmd_adt": "",
        "cmd_chd": "",
        "cmd_inf": "",
        "adt_quantity": 0,
        "chd_quantity": 0,
        "inf_quantity": 0,
    }

    if not seg_numbers:
        return result

    seg_part = ",".join(seg_numbers)

    # mapping suffix
    pax_mapping = {
        "ADT": "",
        "CHD": "-CH",
        "INF": "-INF"
    }

    # mapping field name
    cmd_mapping = {
        "ADT": "cmd_adt",
        "CHD": "cmd_chd",
        "INF": "cmd_inf"
    }

    qty_mapping = {
        "ADT": "adt_quantity",
        "CHD": "chd_quantity",
        "INF": "inf_quantity"
    }

    for pax_type, ticket_numbers in pax_total.items():

        if not ticket_numbers:
            continue

        ticket_part = ",".join(
            str(x) for x in ticket_numbers
        )

        suffix = pax_mapping.get(pax_type, "")

        command = (
            f"FXQ/R{doituong}{suffix},"
            f"U/S{seg_part}/"
            f"T{ticket_part}"
        )

        result[
            cmd_mapping[pax_type]
        ] = command

        result[
            qty_mapping[pax_type]
        ] = len(ticket_numbers)

    return result




async def check_price_stu_vna(
    qualtity,
    dep,
    arr,
    depdate,
    deptime,
    deptimedone,
    
    arrdate=None,
    arrtime=None,
    arrtimedone=None
):
    """
    Flow:
    1. RT PNR
    2. XE segment cũ
    3. Search trip mới
    4. SS lowest trip
    5. Recheck segment mới
    """
    if qualtity == 1 :
        pnr = "D6WZTV"
    elif qualtity == 2 :
        pnr = "D6XPXO"
    else :
        pnr = "D6Y25V"
    async with httpx.AsyncClient(http2=False, timeout=60) as client:
        try:
            
            
            
            
            
            print(pnr)
            # build search new trip
            searnewtrip = build_search_new_trip(
                dep,
                arr,
                depdate,
                deptime,
                arrdate,
                arrtime
            )
            ssid, res = await send_command(client,"IG", "check_stu")
            print("IG")
            print(searnewtrip)
            ssid, resRt = await send_command(client,"RT" + pnr, "check_stu")
            res_Rt =resRt.json()["model"]["output"]["crypticResponse"]["response"]
            
            print("res_Rt")
            if "INVALID RECORD LOCATOR" in res_Rt.upper():
                return {
                    "status": "mã PNR ko tồn tại"
                }
            # search hành trình mới
            ssid, searnewtrip_res = await send_command(client,searnewtrip, "check_stu")
            
            searnewtrip_parser=AvailabilityParser.parse(searnewtrip_res.json()["model"]["output"]["crypticResponse"]["response"])
            # lấy trip rẻ nhất
            print("searnewtrip_parser")
            ssnewtrip = get_lowest_trip(searnewtrip_parser,qualtity,deptime,deptimedone,arrtime,arrtimedone)
            if not ssnewtrip:
                return {
                    "price" :None,
                    "mess" :"Hết ghế"
                }
            # sell segment mới
            ssid, newRt = await send_command(client,ssnewtrip, "check_stu")
            print(ssnewtrip)
            newRt_parser = newRt.json()["model"]["output"]["crypticResponse"]["response"]
            
            # build recheck

            print("newseg")
            
            ssid, res = await send_command(client,"FXB/RSTU,U", "check_stu")
            print("pricing")
            ssid, resPrice = await send_command(client,"TQT", "check_stu")
            #print(resPrice.json())
            price = get_price_new(resPrice.json()["model"]["output"]["crypticResponse"]["response"])
            print(price)
            ssid, res = await send_command(client,"IG", "check_stu")
            print("IG")
            if price:
                return {
                    "price" :price,
                    "mess" :"OK"
                }
            return None
        except Exception  as e:
            try:

                ssid, res = await send_command(client,"IG", "check_stu")
            except:
                pass
            return {
                    "price" :None,
                    "mess" : e
                }




# import asyncio


# async def main():
#     result = await check_price_stu_vna(
#         2,
#         dep="PUS",
#         arr="HAN",
#         depdate="2026-07-16",
#         deptime="1100",
#         deptimedone="1315"
#         # arrdate="2026-07-20",
#         # arrtime="2100",
#         # arrtimedone="2310"
#     )
# # #     # result = await pre_change_pnr(
# # #     #     pnr="E4BSEW"
# # #     # )
#     print(result)


# if __name__ == "__main__":
#     asyncio.run(main())
