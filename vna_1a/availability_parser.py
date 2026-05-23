import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional


# =========================================================
# MODELS
# =========================================================

@dataclass
class FlightOption:

    index: int

    carrier: str
    flight_number: str

    operating_carrier: Optional[str] = None
    marketing_carrier: Optional[str] = None

    from_airport: str = ""
    to_airport: str = ""
    stops: List[str] = field(default_factory=list)
    departure_time: str = ""
    arrival_time: str = ""

    arrival_plus_day: bool = False

    aircraft: Optional[str] = None
    duration: Optional[str] = None

    booking_classes: Dict[str, str] = field(default_factory=dict)

    operated_by: Optional[str] = None

    codeshare: bool = False

    raw_lines: List[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


@dataclass
class AvailabilityGroup:

    route: str
    date: str

    flights: List[FlightOption] = field(default_factory=list)

    def add_flight(self, flight: FlightOption):
        self.flights.append(flight)

    def to_dict(self):
        return {
            "route": self.route,
            "date": self.date,
            "flights": [f.to_dict() for f in self.flights]
        }


# =========================================================
# PARSER
# =========================================================

class AvailabilityParser:
    CONTINUATION_PATTERN = re.compile(
        r"""
        ^\s*
        ([A-Z0-9]{2})
        \s*
        (\d+)
        .*?
        /([A-Z]{3})
        \s+\d+\s+
        ([A-Z]{3})
        """,
        re.VERBOSE
    )
    HEADER_PATTERN = re.compile(
        r"\*\* .*? \*\* ([A-Z]{3}) .*? (\d{2}[A-Z]{3})",
        re.IGNORECASE
    )

    FLIGHT_START_PATTERN = re.compile(
        r"^\s*\d+\s*(?:[A-Z0-9]{2}:)?[A-Z0-9]{2}\s*\d+",
        re.IGNORECASE
    )

    MAIN_FLIGHT_PATTERN = re.compile(
        r"""
        ^\s*
        (\d+)

        \s*

        (?:
            ([A-Z0-9]{2})
            :
        )?

        \s*

        ([A-Z0-9]{2})

        \s*

        (\d+)
        """,
        re.VERBOSE
    )
    ROUTE_PATTERN = re.compile(
        r"/([A-Z]{3})\s+(?:\d+\s+)?([A-Z]{3})",
        re.IGNORECASE
    )

    TIME_PATTERN = re.compile(
        r"(\d{4})\s+(\d{4})(\+1)?"
    )

    AIRCRAFT_PATTERN = re.compile(
        r"E0/([A-Z0-9]+)"
    )

    DURATION_PATTERN = re.compile(
        r"(\d+:\d+)"
    )

    BOOKING_CLASS_PATTERN = re.compile(
        r"\b([A-Z])([0-9L])\b"
    )
    @classmethod
    def intersect_booking_classes(
        cls,
        class_maps: List[Dict[str, str]]
    ) -> Dict[str, str]:

        if not class_maps:
            return {}

        result = dict(class_maps[0])

        for cmap in class_maps[1:]:

            result = {
                k: v
                for k, v in result.items()
                if k in cmap
            }

        return result
    # =====================================================
    # MAIN PARSE
    # =====================================================

    @classmethod
    def parse(cls, raw_text: str) -> List[AvailabilityGroup]:

        groups: List[AvailabilityGroup] = []

        current_group = None

        lines = raw_text.splitlines()

        current_chunk = []

        for line in lines:

            line = line.rstrip()

            if not line:
                continue

            # =================================================
            # HEADER
            # =================================================

            header_match = cls.HEADER_PATTERN.search(line)

            if header_match:

                # =========================================
                # flush previous chunk
                # =========================================

                if current_chunk and current_group:

                    flight = cls.parse_chunk(current_chunk)

                    if flight:
                        current_group.add_flight(flight)

                    current_chunk = []

                # =========================================
                # create new group
                # =========================================

                route = header_match.group(1)
                date = header_match.group(2)

                current_group = AvailabilityGroup(
                    route=route,
                    date=date
                )

                groups.append(current_group)

                continue

            # =================================================
            # FLIGHT START
            # =================================================

            if cls.is_flight_start(line):

                # save previous chunk
                if current_chunk and current_group:

                    flight = cls.parse_chunk(current_chunk)

                    if flight:
                        current_group.add_flight(flight)

                current_chunk = [line]

            else:

                ignore_lines = [
                    "PASSPORT INFORMATION REQUIRED",
                    ">",
                ]

                if line.strip() in ignore_lines:
                    continue

                if current_chunk:
                    current_chunk.append(line)

        # =====================================================
        # LAST CHUNK
        # =====================================================

        if current_chunk and current_group:

            flight = cls.parse_chunk(current_chunk)

            if flight:
                current_group.add_flight(flight)

        return groups

    # =====================================================
    # CHUNK PARSER
    # =====================================================

    @classmethod
    def parse_chunk(
        cls,
        chunk_lines: List[str]
    ) -> Optional[FlightOption]:

        first_line = chunk_lines[0]

        main_match = cls.MAIN_FLIGHT_PATTERN.search(
            first_line
        )

        if not main_match:
            return None

        (
            index,
            operating_carrier,
            marketing_carrier,
            flight_number
        ) = main_match.groups()

        # =====================================================
        # ROUTE
        # =====================================================

        route_match = cls.ROUTE_PATTERN.search(
            first_line
        )

        from_airport = ""
        to_airport = ""
        stops = ""
        if route_match:

            from_airport = route_match.group(1)
            to_airport = route_match.group(2)

        # =====================================================
        # TIME
        # =====================================================

        time_match = cls.TIME_PATTERN.search(
            first_line
        )

        departure_time = ""
        arrival_time = ""
        arrival_plus_day = False

        if time_match:

            departure_time = time_match.group(1)

            arrival_time = time_match.group(2)

            arrival_plus_day = (
                time_match.group(3) is not None
            )
        for extra_line in chunk_lines[1:]:

            cont_match = cls.CONTINUATION_PATTERN.search(
                extra_line
            )

            if not cont_match:
                continue

            (
                seg_carrier,
                seg_flight,
                seg_from,
                seg_to
            ) = cont_match.groups()

            # stop point
            stops=seg_from

            # final destination
            to_airport = seg_to

            # arrival time from last segment
            time_match = cls.TIME_PATTERN.search(
                extra_line
            )

            if time_match:

                arrival_time = time_match.group(2)

                arrival_plus_day = (
                    time_match.group(3) is not None
                )
        # =====================================================
        # AIRCRAFT
        # =====================================================

        aircraft = None

        aircraft_match = cls.AIRCRAFT_PATTERN.search(
            first_line
        )

        if aircraft_match:
            aircraft = aircraft_match.group(1)

        # =====================================================
        # DURATION
        # =====================================================

        duration = None

        duration_match = cls.DURATION_PATTERN.findall(
            first_line
        )

        if duration_match:
            duration = duration_match[-1]

        # =====================================================
        # BOOKING CLASSES
        # =====================================================

        segment_class_maps = []

        current_classes = None

        for line in chunk_lines:

            # new segment
            if (
                cls.is_flight_start(line)
                or cls.CONTINUATION_PATTERN.search(line)
            ):

                if current_classes:
                    segment_class_maps.append(
                        current_classes
                    )

                current_classes = {}

                # parse booking class ngay trên line segment
                line_classes = cls.parse_booking_classes(
                    line
                )

                current_classes.update(line_classes)

                continue

            # booking class line
            if current_classes is not None:

                line_classes = cls.parse_booking_classes(
                    line
                )

                current_classes.update(line_classes)

        # append last segment
        if current_classes:
            segment_class_maps.append(current_classes)

        booking_classes = cls.intersect_booking_classes(
            segment_class_maps
        )

        # =====================================================
        # OPERATED BY
        # =====================================================

        operated_by = None

        for line in chunk_lines:

            if "OPERATED BY" in line.upper():

                operated_by = (
                    line.replace("OPERATED BY", "")
                    .strip()
                )

        # =====================================================
        # BUILD OBJECT
        # =====================================================

        is_codeshare = operating_carrier is not None

        flight = FlightOption(
            index=int(index),

            carrier=marketing_carrier,
            flight_number=flight_number,

            operating_carrier=operating_carrier,
            marketing_carrier=marketing_carrier,

            from_airport=from_airport,
            to_airport=to_airport,

            departure_time=departure_time,
            arrival_time=arrival_time,

            arrival_plus_day=arrival_plus_day,

            aircraft=aircraft,
            duration=duration,

            booking_classes=booking_classes,

            operated_by=operated_by,
            stops=stops,
            codeshare=is_codeshare,

            #raw_lines=chunk_lines
        )

        return flight

    # =====================================================
    # HELPERS
    # =====================================================

    @classmethod
    def is_flight_start(cls, line: str) -> bool:

        return bool(
            cls.FLIGHT_START_PATTERN.search(line)
        )

    @classmethod
    def parse_booking_classes(
        cls,
        text: str
    ) -> Dict[str, str]:

        # remove equipment section
        text = re.sub(r"E0/[A-Z0-9]+", "", text)

        matches = cls.BOOKING_CLASS_PATTERN.findall(
            text
        )

        result = {}

        for cls_code, value in matches:
            result[cls_code] = value

        return result
