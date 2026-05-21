from datetime import datetime
from backendapi1a import send_command
import httpx
from vna_1a.pnr_parser import SegmentParser
from vna_1a.availability_parser import AvailabilityParser
    
def build_search_new_trip(dep, arr, depdate, deptime, arrdate, arrtime):
    """
    Build command dạng:
    anvn17JULICN HAN1005*19JUL1635
    """

    dep_dt = datetime.strptime(depdate, "%Y-%m-%d")
    arr_dt = datetime.strptime(arrdate, "%Y-%m-%d")

    dep_str = dep_dt.strftime("%d%b").upper()
    arr_str = arr_dt.strftime("%d%b").upper()

    return f"anvn{dep_str}{dep} {arr}{deptime}*{arr_str}{arrtime}"


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

    return f"FXQ/RVFR,U/S{','.join(seg_numbers)}"


async def change_pnr(
    pnr,
    dep,
    arr,
    depdate,
    deptime,
    arrdate,
    arrtime,
    seg_del
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
        # load pnr
        await send_command(client,"IG", "change_pnr")
        print("IG")
        ssid, resRt = await send_command(client,"RT" + pnr, "change_pnr")
        res_Rt =resRt.json()["model"]["output"]["crypticResponse"]["response"]
        
        #print(res_Rt)
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
        #print(searnewtrip)
        searnewtrip_parser=AvailabilityParser.parse(searnewtrip_res.json()["model"]["output"]["crypticResponse"]["response"])
        # lấy trip rẻ nhất
        #print(searnewtrip_parser)
        ssnewtrip = get_lowest_trip(searnewtrip_parser,num_customer)

        # sell segment mới
        ssid, newRt = await send_command(client,ssnewtrip, "change_pnr")
        print(ssnewtrip)
        newRt_parser = newRt.json()["model"]["output"]["crypticResponse"]["response"]
        newseg = SegmentParser.parse(newRt_parser)
        # build recheck
        #print(newseg)
        recheck = get_newseg(newseg)
        ssid, res = await send_command(client,"TTE/ALL", "change_pnr")
        # recheck segment
        print(res)
        ssid, price_res = await send_command(client,recheck, "change_pnr")
        print(recheck)
        print(price_res.json())
        ssid, res = await send_command(client,"IG", "change_pnr")
        print("IG")
        return {
            "status": "success",
            "search_command": searnewtrip,
            "sell_command": ssnewtrip,
            "recheck_command": recheck
        }





import asyncio


async def main():
    result = await change_pnr(
        pnr="E4BSEW",
        dep="ICN",
        arr="HAN",
        depdate="2026-07-16",
        deptime="1005",
        arrdate="2026-07-20",
        arrtime="1635",
        seg_del="2,3"
    )

    print(result)


if __name__ == "__main__":
    asyncio.run(main())