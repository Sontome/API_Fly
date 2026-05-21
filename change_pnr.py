from datetime import datetime
from math import e
from backendapi1a import send_command
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
    # =========================
    # CASE 1: Có dòng TOTAL
    # =========================
    total_match = re.search(
        r"TOTAL\s+(\d+)\s+(\d+)\s+\d+\s+(\d+)",
        raw
    )

    if total_match:
        penalty_total = int(total_match.group(1))
        grd_total = int(total_match.group(3))

        return {
            "penalty_total": penalty_total,
            "GRD_TOTAL": grd_total,
            "total_new": penalty_total + grd_total
        }

    # =========================
    # CASE 2: Không có TOTAL
    # =========================

    # Lấy TICKET DIFFERENCE
    grd_match = re.search(
        r"TICKET DIFFERENCE\s+KRW\s+(\d+)",
        raw
    )

    # Lấy PENALTY
    penalty_match = re.search(
        r"PENALTY\s+KRW\s+(\d+)",
        raw
    )

    if grd_match and penalty_match:
        grd_total = int(grd_match.group(1))
        penalty_total = int(penalty_match.group(1))

        return {
            "penalty_total": penalty_total,
            "GRD_TOTAL": grd_total,
            "total_new": penalty_total + grd_total
        }

    return None
def get_lowest_trip(groups, num):
    """
    Return:
    SS2T1*T11

    Logic:
    - group đầu: SS đầy đủ
    - group sau: chỉ {class}{index}
    """

    ss_parts = []

    for i, group in enumerate(groups):

        if not group.flights:
            continue

        flight = group.flights[0]

        booking_classes = flight.booking_classes

        valid_class = None

        # lấy hạng thấp nhất còn đủ ghế
        for cls, seat in reversed(list(booking_classes.items())):

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
                f"SS{num}{valid_class}{flight.index}"
            )

        # group sau
        else:
            ss_parts.append(
                f"{valid_class}{flight.index}"
            )

    return "*".join(ss_parts)

def get_newseg(segs):

    seg_numbers = []

    for seg in segs:

        if getattr(seg.status, "value", "") == "FLOWN":
            continue

        seg_numbers.append(
            str(seg.seg_no)
        )

    if not seg_numbers:
        return ""

    return f"FXQ/R,U/S{','.join(seg_numbers)}"


async def change_pnr(
    pnr,
    dep,
    arr,
    depdate,
    deptime,
    
    seg_del=None,
    arrdate=None,
    arrtime=None,
):
    """
    Flow:
    1. RT PNR
    2. XE segment cũ
    3. Search trip mới
    4. SS lowest trip
    5. Recheck segment mới
    """
    async with httpx.AsyncClient(http2=False, timeout=60) as client:
        try:
            # load pnr
            await send_command(client,"IG", "change_pnr")
            print("IG")
            ssid, resRt = await send_command(client,"RT" + pnr, "change_pnr")
            res_Rt =resRt.json()["model"]["output"]["crypticResponse"]["response"]
            
            print("res_Rt")
            if "INVALID RECORD LOCATOR" in res_Rt.upper():
                return {
                    "status": "mã PNR ko tồn tại"
                }
            num_customer = SegmentParser.get_number_person(res_Rt)
            print(num_customer)
            # delete segment cũ
            ssid, res = await send_command(client,"XE" + str(seg_del), "change_pnr")
            print("XE" + str(seg_del))
            print(res)
            # build search new trip
            searnewtrip = build_search_new_trip(
                dep,
                arr,
                depdate,
                deptime,
                arrdate,
                arrtime
            )

            # search hành trình mới
            ssid, searnewtrip_res = await send_command(client,searnewtrip, "change_pnr")
            print("searnewtrip")
            searnewtrip_parser=AvailabilityParser.parse(searnewtrip_res.json()["model"]["output"]["crypticResponse"]["response"])
            # lấy trip rẻ nhất
            print("searnewtrip_parser")
            ssnewtrip = get_lowest_trip(searnewtrip_parser,num_customer)

            # sell segment mới
            ssid, newRt = await send_command(client,ssnewtrip, "change_pnr")
            print(ssnewtrip)
            newRt_parser = newRt.json()["model"]["output"]["crypticResponse"]["response"]
            newseg = SegmentParser.parse(newRt_parser)
            # build recheck
            print(newseg)
            recheck = get_newseg(newseg)
            ssid, res = await send_command(client,"TTE/ALL", "change_pnr")
            # recheck segment
            print(res)
            ssid, price_res = await send_command(client,recheck, "change_pnr")
            print(recheck)
            
            price_raw= price_res.json()["model"]["output"]["crypticResponse"]["response"]
            print(price_raw)
            new_price = get_price_new(price_raw)
            ssid, res = await send_command(client,"IG", "change_pnr")
            print("IG")
            return {
                "status": "success",
                "search_command": searnewtrip,
                "seg_new": newseg,
                "new_price": new_price
            }
        except Exception  as e:
            try:

                ssid, res = await send_command(client,"IG", "change_pnr")
            except:
                pass
            return {
                "status": "error",
                "search_command": "error",
                "seg_new": "error",
                "new_price": "error",
                "error":e
            }




async def pre_change_pnr(
    pnr
):
    """
    Flow:
    1. RT PNR
    2. IG
    """
    async with httpx.AsyncClient(http2=False, timeout=60) as client:
        # load pnr
        ssid, res = await send_command(client,"IG", "change_pnr")
        print(res)
        ssid, resRt = await send_command(client,"RT" + pnr, "change_pnr")
        res_Rt =resRt.json()["model"]["output"]["crypticResponse"]["response"]
        if "INVALID RECORD LOCATOR" in res_Rt.upper():
            ssid, res = await send_command(client,"IG", "change_pnr")
            return {
                "status": "mã PNR ko tồn tại"
            }
        seg=SegmentParser.parse(res_Rt)
        ssid, res = await send_command(client,"IG", "change_pnr")
        return {
                "seg": seg
            }



# import asyncio


# async def main():
#     result = await change_pnr(
#         pnr="D3FUWB",
#         dep="ICN",
#         arr="HAN",
#         depdate="2026-07-16",
#         deptime="1005",
#         arrdate="2026-07-20",
#         arrtime="1635",
#         seg_del="2,3"
#     )
#     # result = await pre_change_pnr(
#     #     pnr="E4BSEW"
#     # )
#     print(result)


# if __name__ == "__main__":
#     asyncio.run(main())
