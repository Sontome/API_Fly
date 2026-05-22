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

    total_match = re.search(
        r"TOTAL\s+(-?\d+)\s+(-?\d+)\s+\d+\s+(-?\d+)",
        raw
    )

    if total_match:
        penalty_total = int(total_match.group(1))
        total = int(total_match.group(3))
        grd_total = total -penalty_total
        return {
            "penalty_total": penalty_total,
            "GRD_TOTAL": grd_total,
            "total_new": penalty_total + grd_total
        }

    grd_match = re.search(
        r"GRAND TOTAL\s+KRW\s+(-?\d+)",
        raw
    )

    penalty_match = re.search(
        r"PENALTY\s+KRW\s+(-?\d+)",
        raw
    )

    if grd_match and penalty_match:
        total = int(grd_match.group(1))
        penalty_total = int(penalty_match.group(1))
        grd_total = total -penalty_total
        return {
            "penalty_total": penalty_total,
            "GRD_TOTAL": grd_total,
            "total_new": penalty_total + grd_total
        }

    return None
def get_lowest_trip(
    groups,
    num,
    class_lowest,
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
    - nhưng không thấp hơn class_lowest

    Chọn đúng segment theo:
    - chiều đi:
        departure_time == deptime
        arrival_time   == deptimedone

    - chiều về:
        departure_time == arrtime
        arrival_time   == arrtimedone
    """

    # thứ tự hạng cố định
    CLASS_ORDER = [
        "F", "A", "J", "C", "D", "I",
        "W", "S",
        "Y", "B", "M", "H", "K",
        "L", "Q", "N", "R", "T", "E"
    ]

    def normalize_time(t):
        """
        Convert về HHMM
        Ví dụ:
        8:30 -> 0830
        0830 -> 0830
        08:30:00 -> 0830
        """
        if not t:
            return None

        t = str(t).strip()

        # bỏ :
        t = t.replace(":", "")

        # nếu có giây HHMMSS -> lấy HHMM
        if len(t) >= 6:
            t = t[:4]

        # padding
        t = t.zfill(4)

        return t

    # normalize time
    deptime = normalize_time(deptime)
    deptimedone = normalize_time(deptimedone)

    arrtime = normalize_time(arrtime)
    arrtimedone = normalize_time(arrtimedone)

    ss_parts = []

    for i, group in enumerate(groups):

        if not group.flights:
            continue

        selected_flight = None

        # tìm đúng segment
        for flight in group.flights:

            dep = normalize_time(
                getattr(flight, "departure_time", None)
            )

            arr = normalize_time(
                getattr(flight, "arrival_time", None)
            )

            # chiều đi
            if dep == deptime and arr == deptimedone:
                selected_flight = flight
                break

            # chiều về
            if (
                arrtime
                and arrtimedone
                and dep == arrtime
                and arr == arrtimedone
            ):
                selected_flight = flight
                break

        if not selected_flight:
            continue

        booking_classes = selected_flight.booking_classes

        valid_class = None

        # index của class_lowest
        try:
            lowest_index = CLASS_ORDER.index(class_lowest[i])
        except ValueError:
            lowest_index = len(CLASS_ORDER) - 1

        # duyệt từ thấp -> cao
        for cls in reversed(CLASS_ORDER):

            # class không tồn tại
            if cls not in booking_classes:
                continue

            # bỏ qua hạng thấp hơn class_lowest
            if CLASS_ORDER.index(cls) > lowest_index:
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
        "CHD": "-CHD",
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




async def change_pnr(
    pnr,
    dep,
    arr,
    depdate,
    deptime,
    deptimedone,
    seg_del=None,
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
    async with httpx.AsyncClient(http2=False, timeout=60) as client:
        try:
            infoPnr = await checkmatvechoVNA(pnr,"precheckchangeVNA")
            doituong = (infoPnr or {}).get("doituong", "")
            if doituong == "ADT":
                doituong = ""
            # load pnr
            await send_command(client,"IG", "change_pnr")
            print(doituong)
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
            class_old = SegmentParser.get_class_seg(res_Rt,seg_del)
            print(class_old)
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
            print(searnewtrip)
            searnewtrip_parser=AvailabilityParser.parse(searnewtrip_res.json()["model"]["output"]["crypticResponse"]["response"])
            # lấy trip rẻ nhất
            print("searnewtrip_parser")
            ssnewtrip = get_lowest_trip(searnewtrip_parser,num_customer,class_old,deptime,deptimedone,arrtime,arrtimedone)

            # sell segment mới
            ssid, newRt = await send_command(client,ssnewtrip, "change_pnr")
            print(ssnewtrip)
            newRt_parser = newRt.json()["model"]["output"]["crypticResponse"]["response"]
            newseg = SegmentParser.parse(newRt_parser)
            # build recheck

            print(newseg)
            if ")>" in newRt_parser:
                print("MD page 2")    
                ssid, newRt_page2 = await send_command(
                    client,
                    "MD",
                    "change_pnr"
                )

                newRt_parser += (
                    "\n" +
                    newRt_page2.json()["model"]["output"]["crypticResponse"]["response"]
                )
            pax_total= SegmentParser.get_pax_FHE(newRt_parser)
            print(pax_total)
            recheck = get_newseg(newseg,pax_total,doituong)
            total_price = {
                "penalty_total": 0,
                "GRD_TOTAL": 0,
                "total_new": 0
            }

            cmd_list = [
                ("ADT", recheck.get("cmd_adt"),recheck.get("adt_quantity")),
                ("CHD", recheck.get("cmd_chd"),recheck.get("chd_quantity")),
                ("INF", recheck.get("cmd_inf"),recheck.get("inf_quantity")),
            ]

            for pax_type, cmd,soluong in cmd_list:

                if not cmd:
                    continue

                print(f"RECHECK {pax_type}: {cmd}")

                ssid, price_res = await send_command(
                    client,
                    cmd,
                    "change_pnr"
                )

                price_raw = (
                    price_res.json()["model"]["output"]
                    ["crypticResponse"]["response"]
                )
                if soluong == 1 :
                    ssid, price_res_2 = await send_command(
                        client,
                        "MD",
                        "change_pnr"
                    )

                    price_raw = (
                        price_res_2.json()["model"]["output"]
                        ["crypticResponse"]["response"]
                    )
                    
                print(price_raw)

                new_price = get_price_new(price_raw)

                # cộng dồn
                total_price["penalty_total"] += (
                    new_price.get("penalty_total", 0)
                )

                total_price["GRD_TOTAL"] += (
                    new_price.get("GRD_TOTAL", 0)
                )

                total_price["total_new"] += (
                    new_price.get("total_new", 0)
                )

            print("TOTAL:", total_price)
            ssid, res = await send_command(client,"IG", "change_pnr")
            print("IG")
            return {
                "status": "success",
                "search_command": searnewtrip,
                "seg_new": newseg,
                "new_price": total_price
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
#         pnr="ETZAHK",
#         dep="PUS",
#         arr="HAN",
#         depdate="2026-07-16",
#         deptime="1100",
#         deptimedone="1315",
#         # arrdate="2026-07-20",
#         # arrtime="1635",
#         # arrtimedone="1635",
#         seg_del="3"
#     )
# #     # result = await pre_change_pnr(
# #     #     pnr="E4BSEW"
# #     # )
#     print(result)


# if __name__ == "__main__":
#     asyncio.run(main())
