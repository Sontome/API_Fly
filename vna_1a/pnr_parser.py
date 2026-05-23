import re
from enum import Enum
from dataclasses import dataclass, asdict
from typing import List, Optional


class SegmentStatus(Enum):
    FLOWN = "FLOWN"
    TICKETED = "TICKETED"
    HOLDING = "HOLDING"
    CONFIRMED = "CONFIRMED"
    WAITLIST = "WAITLIST"
    UNKNOWN = "UNKNOWN"


@dataclass
class Segment:
    seg_no: int
    carrier: str
    flight_number: str
    booking_class: str
    day: str
    dow: str
    trip: str
    from_airport: str
    to_airport: str

    status_code: str
    status: SegmentStatus

    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    arrival_day: Optional[str] = None

    ticketed: bool = False
    flown: bool = False
    holding: bool = False

    def to_dict(self):
        data = asdict(self)
        data["status"] = self.status.value
        return data


class SegmentStatusResolver:

    @staticmethod
    def resolve(status_code: str) -> SegmentStatus:

        if status_code == "FLWN":
            return SegmentStatus.FLOWN

        if status_code.startswith("TK"):
            return SegmentStatus.TICKETED

        if status_code.startswith("DK"):
            return SegmentStatus.HOLDING

        if status_code.startswith("HK"):
            return SegmentStatus.CONFIRMED

        if status_code.startswith("HL"):
            return SegmentStatus.WAITLIST

        return SegmentStatus.UNKNOWN


class SegmentParser:
    PASSENGER_PATTERN = re.compile(
        r"""
        \b
        (\d+)
        \.
        [A-Z]+
        /
        [A-Z\s\-]+
        \s+
        (MR|MS|MRS|MISS|MSTR|CHD|INF)
        \(
        (ADT|CNN|CHD|INF)
        (?:/[0-9A-Z]+)?
        \)
        """,
        re.VERBOSE
    )
    PASSENGER_PATTERN_NAME = re.compile(
        r"""
        \b
        (\d+)                                      # pax no
        \.
        
        (
            [A-Z]+
            /
            [A-Z\s\-]+?
        )                                          # full name
        
        \s+
        
        (MR|MS|MRS|MISS|MSTR|CHD|INF)              # title
        
        \(
        (ADT|CNN|CHD|INF)
        (?:/[0-9A-Z]+)?
        \)

        (                                          
            \(
            INF[^)]*
            \)
        )?                                         # optional infant block
        """,
        re.VERBOSE
    )
    SEGMENT_PATTERN = re.compile(
        r"""
        ^\s*
        (\d+)                             # seg no
        \s+
        
        ([A-Z0-9]{2})                    # carrier
        \s*                              # optional space
        
        (\d{1,4})                        # flight number
        
        \s+
        ([A-Z])                          # booking class
        
        \s+
        (\d{2}[A-Z]{3})                  # departure day
        
        \s+
        (\d)                             # dow
        
        (?:\*|\s)?                       # optional * or space
        
        ([A-Z]{6})                       # route
        
        \s+
        
        (FLWN|[A-Z]{2}\d+)               # status
        
        (?:\s+(\d{4}))?                  # dep time
        (?:\s+(\d{4}))?                  # arr time
        (?:\s+(\d{2}[A-Z]{3}))?          # arr day
        
        """,
        re.VERBOSE
    )
    @staticmethod
    def get_person_name(raw_text: str) -> List[str]:

        result = []

        matches = SegmentParser.PASSENGER_PATTERN_NAME.findall(
            raw_text.upper()
        )

        for match in matches:

            full_name = match[1].strip()
            type=match[3].strip()
            infant_block = match[4]

            # normalize name
            full_name = re.sub(r"\s+", " ", full_name) +f" {type} "
            full_name = re.sub(r"\s*/\s*", "/", full_name)

            # có INF attach
            if infant_block:

                infant_text = infant_block.strip("()")

                # normalize infant
                infant_text = re.sub(r"\s+", " ", infant_text)

                full_name = f"{full_name} {type} ({infant_text})"

            result.append(full_name)

        return result
    @staticmethod
    def get_person_type(raw_text: str) -> dict:
        """
        Map vị trí pax:
        P1 -> ADT
        P2 -> CHD
        """

        result = {}

        matches = SegmentParser.PASSENGER_PATTERN.findall(
            raw_text.upper()
        )

        for idx, match in enumerate(matches, start=1):

            pax_type = match[2]

            if pax_type in ("CNN", "CHD"):
                pax_type = "CHD"

            else:
                pax_type = "ADT"

            result[idx] = pax_type

        return result
    @staticmethod
    def get_pax_FHE(raw_text: str) -> dict:

        result = {
            "ADT": set(),
            "CHD": set(),
            "INF": set()
        }

        lines = raw_text.splitlines()

        person_type_map = SegmentParser.get_person_type(raw_text)

        # =========================================
        # helper
        # =========================================

        def process_line(line: str):

            line = line.strip().upper()

            match = re.search(
                r"""
                ^
                (\d+)                      # line no
                \s+
                (FHE|FA)
                \s+
                (PAX|CHD|INF)
                \b
                .*?
                (?:/P(\d+))?               # optional /P1
                \s*$
                """,
                line,
                re.VERBOSE
            )

            if not match:
                return

            line_no, _, raw_type, pax_no = match.groups()

            line_no = int(line_no)

            # =====================================
            # INF -> bắt trực tiếp
            # =====================================

            if raw_type == "INF":
                result["INF"].add(line_no)
                return

            # =====================================
            # ADT / CHD -> lookup theo pax position
            # =====================================

            pax_no = int(pax_no) if pax_no else 1

            pax_type = person_type_map.get(pax_no, "ADT")

            if pax_type == "CHD":
                result["CHD"].add(line_no)
            else:
                result["ADT"].add(line_no)

        # =========================================
        # PASS 1: FHE
        # =========================================

        found_fhe = False

        for line in lines:

            if re.search(r"^\d+\s+FHE\b", line.strip().upper()):
                found_fhe = True
                process_line(line)

        # =========================================
        # PASS 2: fallback FA
        # =========================================

        if not found_fhe:

            for line in lines:

                if re.search(r"^\d+\s+FA\b", line.strip().upper()):
                    process_line(line)

        # =========================================
        # RESULT
        # =========================================

        return {
            "ADT": sorted(result["ADT"]),
            "CHD": sorted(result["CHD"]),
            "INF": sorted(result["INF"])
        }
    @staticmethod
    def get_number_person(raw_text: str) -> int:

        matches = SegmentParser.PASSENGER_PATTERN.findall(
            raw_text.upper()
        )

        return len(matches)
    @staticmethod
    def get_class_seg(raw_text: str, seg_del) -> List[str]:

        segments = SegmentParser.parse(raw_text)

        # convert seg_del thành list int
        if isinstance(seg_del, str):
            seg_numbers = [
                int(x.strip())
                for x in seg_del.split(",")
                if x.strip().isdigit()
            ]
        else:
            seg_numbers = [int(seg_del)]

        # lấy booking_class theo seg_no
        result = [
            seg.booking_class
            for seg in segments
            if seg.seg_no in seg_numbers
        ]

        # luôn trả về 2 phần tử
        if not result:
            result = [None, None]

        elif len(result) == 1:
            result = [result[0], result[0]]

        else:
            result = [result[0], result[-1]]

        return result
    @classmethod
    def parse(cls, raw_text: str) -> List[Segment]:

        segments = []

        lines = raw_text.splitlines()

        for line in lines:

            line = line.rstrip()

            match = cls.SEGMENT_PATTERN.search(line)

            if not match:
                continue

            (
                seg_no,
                carrier,
                flight_number,
                booking_class,
                day,
                dow,
                trip,
                status_code,
                departure_time,
                arrival_time,
                arrival_day
            ) = match.groups()

            from_airport = trip[:3]
            to_airport = trip[3:]

            status = SegmentStatusResolver.resolve(status_code)

            segment = Segment(
                seg_no=int(seg_no),
                carrier=carrier,
                flight_number=flight_number,
                booking_class=booking_class,
                day=day,
                dow=dow,
                trip=trip,
                from_airport=from_airport,
                to_airport=to_airport,
                status_code=status_code,
                status=status,
                departure_time=departure_time,
                arrival_time=arrival_time,
                arrival_day=arrival_day,
                ticketed=status == SegmentStatus.TICKETED,
                flown=status == SegmentStatus.FLOWN,
                holding=status == SegmentStatus.HOLDING
            )

            segments.append(segment)

        return segments


# =========================
# TEST
# =========================

# raw = "--- TST RLR RLP DCS ---\nRP/SELVN28AA/SELVN28AA            GH/SU  16MAY26/0838Z   D6OJ5O\n  1.LE/TUAN VIET MR(ADT)\n  2  VN 415 T 16MAY 6 ICNHAN         FLWN\n  3  VN 416 T 22MAY 5 HANICN TK1  2335 0550  23MAY  E  VN/D6OJ5O\n  4 AP HCMC 01035463396\n  5 APE HANVIETAIR.SERVICE@GMAIL.COM\n  6 APE HANVIETAIR.SERVICE@GMAIL.COM\n  7 APE HANVIETAIR247@GMAIL.COM\n  8 APM +82 1035463396\n  9 APM +82 1035463396\n 10 APM +82 1021511790\n 11 APN E+HANVIETAIR.SERVICE@GMAIL.COM/VI\n 12 TK OK28DEC/SELVN28AA//ETVN\n 13 SSR RQST VN KK1 ICNHAN/17CN,P1/FLWN/S2   SEE RTSTR\n 14 *SSR FQTV VN HK/ VN9005270707 ELITE\n 15 SSR DOCS VN HK1 P/VNM/E02924250/VNM/14JUL88/M/24JAN35/LE/TUA\n       N VIET\n 16 SSR DOCS VN HK1 P/VNM/E02924250/VNM/14JUL88/M/24JAN35/LE/TUA\n       N VIET/S2\n 17 FA PAX 738-2317402467/ETVN/28DEC25/SELVN28AA/17915015/S2-3\n 18 FB PAX 0000000000 TTP/T1/T-VN/ITR-EMLA/LA-VI OK ETICKET/S2-3\n 19 FE PAX NON-END.RESTRICT MAY APPLYCONTACT B4 DEPT FOR CHANGE\n)>"

#raw = "--- TST RLR MSC ---\nRP/SELVN28AA/SELVN28AA            WS/SU  21MAY26/1351Z   E8J6L3\n  1.LUONG/THI THU PHUONG(ADT)   2.MOON/GOEUN(CHD/03MAY19)\n  3  VN 417 R 23JUL 4*ICNHAN HK2  1005 1235  23JUL  E  VN/E8J6L3\n  4  VN1717 R 23JUL 4*HANVII HK2  1720 1815  23JUL  E  VN/E8J6L3\n  5  VN1718 R 15AUG 6*VIIHAN HK2  1850 1945  15AUG  E  VN/E8J6L3\n  6  VN 416 R 15AUG 6*HANICN HK2  2335 0550  16AUG  E  VN/E8J6L3\n  7 APE LETHIPHUONGTHUY2212@GMAIL.COM\n  8 APE LETHIPHUONGTHUY2212@GMAIL.COM/P1\n  9 APM +84 914360360\n 10 APM +84 914360360/P1\n 11 APN M+84914360360/VI/P1\n 12 APN E+LETHIPHUONGTHUY2212@GMAIL.COM/VI/P1\n 13 TK PAX OK21MAY/SELVN28AA//ETVN/S3-6/P1-2\n 14 SSR CHLD VN HK1 03MAY19/P2\n 15 FA PAX 738-2321092706/ETVN/21MAY26/SELVN28AA/17915015\n       /S3-6/P1\n 16 FA PAX 738-2321092707/ETVN/21MAY26/SELVN28AA/17915015\n       /S3-6/P2\n 17 FB PAX 0000000000 TTP/T1-2/T-VN/ITR-EMLA/LA-VI OK ETICKET\n       /S3-6/P1\n 18 FB PAX 0000000001 TTP/T1-2/T-VN/ITR-EMLA/LA-VI OK ETICKET\n       /S3-6/P2\n)>"
#raw ="TICKET REVALIDATION/REISSUE IS RECOMMENDED\n--- TST RLR ---\nRP/SELVN28AA/SELVN28AA            WS/SU   5MAY26/0419Z   ETZAHK\n  1.DO/HUU LAM MR(ADT)   2.NGUYEN/THI KIEU PHUONG MS(ADT)\n  3 AP HCMC 01035463396\n  4 APE HANVIETAIR.SERVICE@GMAIL.COM\n  5 APE HANVIETAIR.SERVICE@GMAIL.COM/P1\n  6 APE HANVIETAIR247@GMAIL.COM/P1\n  7 APM +82 1035463396\n  8 APM +82 1035463396/P1\n  9 APM +82 1021511790/P1\n 10 APN E+HANVIETAIR.SERVICE@GMAIL.COM/VI/P1\n 11 FHE PAX 738-2320659730/P2\n 12 FHE PAX 738-2320659731/P1\n>"
# raw = "--- TST AXR RLR DCS ---\nRP/SELVN28AA/SELVN28AA            WS/SU  23MAY26/0250Z   EXAQFB\n  1.DO/JIHO MSTR(CHD/18NOV21)\n  2  VN 423 N 16MAY 6 PUSSGN         FLWN\n  3  VN 422 N 03JUN 3 SGNPUS HK1  0110 0750  03JUN  E  VN/EXAQFB\n  4 AP HCMC 01035463396\n  5 APE HANVIETAIR.SERVICE@GMAIL.COM\n  6 APM +82 1035463396\n  7 TK OK23MAY/SELVN28AA\n  8 TK PAX OK23MAY/SELVN28AA//ETVN/S3\n  9 SSR RQST VN KK1 PUSSGN/29BN,P1/FLWN/S2   SEE RTSTR\n 10 SSR CHLD VN HK1 18NOV21\n 11 SSR DOCS VN HK1 P/KOR/M395H3239/KOR/18NOV21/M/22JUL27/DO/JIH\n       O\n 12 SSR DOCS VN HK1 P/KOR/M395H3239/KOR/18NOV21/M/22JUL27/DO/JIH\n       O/S2\n 13 FA PAX 738-2320866781/ETVN/15MAY26/SELVN28AA/17915015/S2\n 14 FA PAX 738-2321092730/ETVN/23MAY26/SELVN28AA/17915015/S3\n 15 FHE PAX 738-2320866732\n 16 FB PAX 0000000001 TTP/T5-6/T-VN/ITR-EMLA/LA-VI OK ETICKET/S2\n 17 FB PAX 0000000000 TTP/T2/T-VN/ITR-EMLA OK ETICKET/S3\n 18 FE PAX KRW60000 NONREF - NON-END.RESTRICT MAY APPLYCONTACT\n       B4 DEPT FOR CHANGE/S3\n)>"

# # segments = SegmentParser.parse(raw)
# # segments = SegmentParser.get_class_seg(raw,"3")
# # #segments = SegmentParser.get_pax_FHE(raw)
# # print(segments)
# # segments = SegmentParser.get_number_person(raw)
# #segments = SegmentParser.get_pax_FHE(raw)
# segments = SegmentParser.get_person_name(raw)
# print(segments)
# # # # for seg in segments:
    
# # #     print(seg.to_dict())
