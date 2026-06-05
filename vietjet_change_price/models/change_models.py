"""
models/change_models.py
Typed data models for VietJet change price flow.
Uses dataclasses for zero dependencies.
Parser detail will be implemented separately.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Input / Request Models
# ---------------------------------------------------------------------------

@dataclass
class ChangeRequest:
    """
    Represents a user's request to get a price quote for changing one leg.
    Used as input to ChangeQuotationService.
    """
    pnr: str
    dep: str                    # Departure airport code, e.g. "HAN"
    arr: str                    # Arrival airport code, e.g. "SGN"
    dep_date: str               # Format: "YYYY-MM-DD"
    new_flight_no: str          # e.g. "VJ123"
            
     
    segdel: int = 0  # xóa hết 2 chặng là 99
    arr_date:str =None              # Format: "YYYY-MM-DD"
    new_flight_arr_no: str =None 
@dataclass
class PassengersQuatity:
    adt: int
    chd: int                   
    inf: int  


@dataclass
class TwoLegChangeRequest:
    """Input for quoting both departure and return legs."""
    departure: ChangeRequest
    return_: ChangeRequest


# ---------------------------------------------------------------------------
# PNR / Booking Info
# ---------------------------------------------------------------------------

@dataclass
class JourneyInfo:
    """Key identifiers for a single journey (leg) in the PNR."""
    journey_key: str
    booking_key: str
    origin: str
    destination: str
    departure_date: str
    flight_no: str


@dataclass
class PnrInfo:
    """
    Extracted from getinfopnr response.
    Holds reservation key and journey identifiers for both legs.
    """
    pnr: str
    reservation_key: str

    # Departure leg
    departure_journey: JourneyInfo | None = None
    
    # Return leg (None for one-way)
    return_journey: JourneyInfo | None = None
    
    # Raw API response cached here — parser will extract more fields later
    raw_response: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# New Trip Options
# ---------------------------------------------------------------------------

@dataclass
class NewTripOption:
    """
    Extracted from getnewtrip response.
    Represents the selected new flight option.
    """
    new_booking_key: str
    flight_no: str
    origin: str
    destination: str
    departure_time: str | None = None
    arrival_time: str | None = None

    # Raw response cached
    raw_response: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Payment Info
# ---------------------------------------------------------------------------

@dataclass
class PaymentInfo:
    """Extracted from getpaymentkey response."""
    payment_key: str
    payment_method: str | None = None

    # Raw response cached
    raw_response: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Price Quotation
# ---------------------------------------------------------------------------

@dataclass
class PriceQuotation:
    

    # Pricing breakdown — parser will populate these
    total_price_change: float | None = None   # Final amount user pays
    fare_difference: float | None = None      # Fare delta
    change_fee: float | None = None           # Admin/change fee
    reservationCredits:float | None = None  

    

    @property
    def total_cost(self) -> float:
        """Safe accessor — returns 0 if not yet parsed."""
        return self.total_price_change or 0.0


@dataclass
class CombinedQuotation:
    """
    Aggregated result for a two-leg change price quote.
    NOTE: This is a READ-ONLY quote. No booking changes are confirmed.
    """
    departure_quotation: PriceQuotation
    return_quotation: PriceQuotation

    @property
    def total_cost(self) -> float:
        """Sum of both legs."""
        return self.departure_quotation.total_cost + self.return_quotation.total_cost

    @property
    def currency(self) -> str:
        return self.departure_quotation.currency

    @property
    def summary(self) -> dict[str, Any]:
        return {
            "departure_cost": self.departure_quotation.total_cost,
            "return_cost": self.return_quotation.total_cost,
            "total_cost": self.total_cost,
            "currency": self.currency,
            "departure_quoted_at": self.departure_quotation.quoted_at.isoformat(),
            "return_quoted_at": self.return_quotation.quoted_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# Internal Quotation Context (per leg, used within service)
# ---------------------------------------------------------------------------

@dataclass
class LegQuotationContext:
    """
    Internal context object tracking all intermediate state
    for one leg's quotation flow.
    Used by ChangeQuotationService to pass data between steps.
    """
    change_request: ChangeRequest
    pnr_info: PnrInfo | None = None
    new_trip_option: NewTripOption | None = None
    new_trip_return_option: NewTripOption | None = None
    payment_info: PaymentInfo | None = None
    payment_return_info: PaymentInfo | None = None
    quotation: PriceQuotation | None = None
    quotation_return: PriceQuotation | None = None
    passengers:PassengersQuatity | None = None
