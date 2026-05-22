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
        (MR|MS|MRS|MISS|CHD|INF)
        \(
        (ADT|CNN|CHD|INF)
        \)?
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
    def get_number_person(raw_text: str) -> int:

        matches = SegmentParser.PASSENGER_PATTERN.findall(
            raw_text.upper()
        )

        return len(matches)
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

# raw = "--- TST RLR MSC ---\nRP/SELVN28AA/SELVN28AA            WS/SU  21MAY26/1351Z   E8J6L3\n  1.LUONG/THI THU PHUONG(ADT)   2.MOON/GOEUN(CHD/03MAY19)\n  3  VN 417 R 23JUL 4*ICNHAN HK2  1005 1235  23JUL  E  VN/E8J6L3\n  4  VN1717 R 23JUL 4*HANVII HK2  1720 1815  23JUL  E  VN/E8J6L3\n  5  VN1718 R 15AUG 6*VIIHAN HK2  1850 1945  15AUG  E  VN/E8J6L3\n  6  VN 416 R 15AUG 6*HANICN HK2  2335 0550  16AUG  E  VN/E8J6L3\n  7 APE LETHIPHUONGTHUY2212@GMAIL.COM\n  8 APE LETHIPHUONGTHUY2212@GMAIL.COM/P1\n  9 APM +84 914360360\n 10 APM +84 914360360/P1\n 11 APN M+84914360360/VI/P1\n 12 APN E+LETHIPHUONGTHUY2212@GMAIL.COM/VI/P1\n 13 TK PAX OK21MAY/SELVN28AA//ETVN/S3-6/P1-2\n 14 SSR CHLD VN HK1 03MAY19/P2\n 15 FA PAX 738-2321092706/ETVN/21MAY26/SELVN28AA/17915015\n       /S3-6/P1\n 16 FA PAX 738-2321092707/ETVN/21MAY26/SELVN28AA/17915015\n       /S3-6/P2\n 17 FB PAX 0000000000 TTP/T1-2/T-VN/ITR-EMLA/LA-VI OK ETICKET\n       /S3-6/P1\n 18 FB PAX 0000000001 TTP/T1-2/T-VN/ITR-EMLA/LA-VI OK ETICKET\n       /S3-6/P2\n)>"

# segments = SegmentParser.parse(raw)
# print("seg.to_dict(")
# for seg in segments:
    
#     print(seg.to_dict())
