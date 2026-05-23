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
    def get_person_type(raw_text: str) -> dict:
        """
        Xác định loại khách theo position:
        P1 = ADT
        P2 = CHD
        ...

        Return:
        {
            1: "ADT",
            2: "CHD"
        }
        """

        result = {}

        matches = SegmentParser.PASSENGER_PATTERN.findall(
            raw_text.upper()
        )
        print(matches)
        for idx, match in enumerate(matches, start=1):

            pax_type = match[2]

            # normalize
            if pax_type in ("CNN", "CHD"):
                pax_type = "CHD"

            elif pax_type == "INF":
                pax_type = "INF"

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
        # helper parse line
        # =========================================

        def process_line(line: str):

            line = line.strip().upper()

            match = re.search(
                r"""
                ^
                (\d+)                  # line no
                \s+
                (FHE|FA)
                \s+
                (PAX|CHD|INF)
                \b
                .*?
                (?:/P(\d+))?           # optional /P1 /P2
                \s*$
                """,
                line,
                re.VERBOSE
            )

            if not match:
                return

            line_no, _, _, pax_no = match.groups()

            line_no = int(line_no)

            # default P1 nếu không có /P?
            pax_no = int(pax_no) if pax_no else 1

            # lookup pax type thực tế
            pax_type = person_type_map.get(pax_no, "ADT")

            result[pax_type].add(line_no)

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
