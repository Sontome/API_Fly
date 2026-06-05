"""
services/quotation_service.py
ChangeQuotationService — business logic for price change quotation.

Responsibilities:
- Orchestrate 4-step quote flow per leg
- Handle sequential 2-leg quoting (airline does not allow simultaneous)
- Combine quotations without confirming any booking change
- Cache raw responses and intermediate context per request

KEY RULE: This service NEVER:
  - Confirms a booking change
  - Updates booking state
  - Refreshes reservation
  - Fetches new booking state after quoting
"""

import logging
from dataclasses import asdict
from typing import Any

from api.change_api import VietjetChangeAPI
from core.exceptions import QuotationError
from core.session import VietjetSession
from models.change_models import (
    ChangeRequest,
    CombinedQuotation,
    JourneyInfo,
    LegQuotationContext,
    NewTripOption,
    PaymentInfo,
    PnrInfo,
    PriceQuotation,
    TwoLegChangeRequest,
    PassengersQuatity
)
logging.getLogger("httpcore").disabled = True
logging.getLogger("httpx").disabled = True
logger = logging.getLogger(__name__)

def extract_trips(data):
    trips = []

    for seg_no, journey in enumerate(data.get("journeys", []), start=1):
        for segment in journey.get("segments", []):
            trips.append({
                "seg_no": seg_no,
                "flight_no": segment.get("Number"),
                "origin": segment.get("departureAirport", {}).get("Code"),
                "destination": segment.get("arrivalAirport", {}).get("Code"),
                "departure_time": segment.get("ETDLocal"),
                "arrival_time": segment.get("ETALocal"),
            })

    return {"trips": trips}
def build_change_result(ctx):
    trips = []

    if ctx.new_trip_option:
        trips.append({
            "flight_no": ctx.new_trip_option.flight_no,
            "origin": ctx.new_trip_option.origin,
            "destination": ctx.new_trip_option.destination,
            "departure_time": ctx.new_trip_option.departure_time,
            "arrival_time": ctx.new_trip_option.arrival_time,
        })

    if ctx.new_trip_return_option:
        trips.append({
            "flight_no": ctx.new_trip_return_option.flight_no,
            "origin": ctx.new_trip_return_option.origin,
            "destination": ctx.new_trip_return_option.destination,
            "departure_time": ctx.new_trip_return_option.departure_time,
            "arrival_time": ctx.new_trip_return_option.arrival_time,
        })

    quotation = {
        "total_price_change": 0,
        "fare_difference": 0,
        "change_fee": 0,
        "reservationCredits": 0,
    }

    if ctx.quotation:
        quotation["total_price_change"] += ctx.quotation.total_price_change
        quotation["fare_difference"] += ctx.quotation.fare_difference
        quotation["change_fee"] += ctx.quotation.change_fee
        quotation["reservationCredits"] += ctx.quotation.reservationCredits

    if ctx.quotation_return:
        quotation["total_price_change"] += ctx.quotation_return.total_price_change
        quotation["fare_difference"] += ctx.quotation_return.fare_difference
        quotation["change_fee"] += ctx.quotation_return.change_fee
        quotation["reservationCredits"] += ctx.quotation_return.reservationCredits

    return {
        "trips": trips,
        "quotation": quotation
    }

class ChangeQuotationService:
    """
    Business logic service for checking flight change prices.

    Supports:
    - Single-leg quote (departure OR return)
    - Two-leg combined quote (departure AND return)

    Always uses the ORIGINAL reservation_key and journey_keys.
    Does not mutate booking state.

    Args:
        session: VietjetSession instance (handles auth).

    Usage:
        service = ChangeQuotationService(session)

        # Single leg
        quotation = service.quote_single_leg(request)

        # Two legs
        combined = service.quote_two_legs(two_leg_request)
        print(combined.total_cost)
    """

    def __init__(self, session: VietjetSession):
        self._api = VietjetChangeAPI(session)

        # Cache: pnr → PnrInfo (avoid re-fetching for same PNR)
        # self._pnr_cache: dict[str, PnrInfo] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def quote_single_leg(self, request: ChangeRequest):
        """
        Get a price quotation for changing one leg of a booking.

        Flow:
            1. getinfopnr   → reservation_key, old journey/booking keys
            2. getnewtrip   → new_booking_key for selected flight
            3. getpaymentkey → payment_key
            4. getnewprice  → price quotation (READ ONLY — no confirmation)

        Args:
            request: ChangeRequest describing the desired change.

        Returns:
            PriceQuotation with pricing data and cached raw responses.

        Raises:
            QuotationError: If any step in the flow fails.
        """
        logger.info(
            f"[quote_single_leg] PNR={request.pnr} | "
            f"{request.dep}→{request.arr} on {request.dep_date} | segdel : {request.segdel}  "
            
        )

        ctx = LegQuotationContext(change_request=request)

        try:
            ctx = self._step1_get_pnr_info(ctx)

            ctx = self._step2_get_new_trip(ctx)
            ctx = self._step3_get_payment_key(ctx)
            ctx = self._step4_get_new_price(ctx)
            # print(ctx)
        except QuotationError:
            raise
        except Exception as e:
            raise QuotationError(
                f"Quotation flow failed for PNR={request.pnr}: {e}"
            ) from e

        
        
        return build_change_result(ctx)

    def quote_two_legs(self, request: ChangeRequest) :
        """
        Get combined price quotation for changing BOTH departure and return legs.

        Because VietJet does not allow changing 2 legs simultaneously,
        this method quotes each leg SEQUENTIALLY using the ORIGINAL
        reservation state. It does NOT confirm either change.

        Flow:
            1. Quote departure leg  → dep_quotation
            2. Quote return leg     → ret_quotation
            3. Combine totals       → CombinedQuotation

        NOTE: Uses original reservation_key and journey_keys for BOTH legs.
              Does NOT update or reload booking state between legs.

        Args:
            request: TwoLegChangeRequest containing both ChangeRequests.

        Returns:
            CombinedQuotation with breakdown and total.

        Raises:
            QuotationError: If either leg's flow fails.
        """
        logger.info(
            f"[quote_double_leg] PNR={request.pnr} | "
            f"{request.dep}->{request.arr} on {request.dep_date} | {request.arr}<-{request.dep}on {request.arr_date} | segdel : all  "
           
        )

        ctx = LegQuotationContext(change_request=request)

        try:
            ctx = self._step1_get_pnr_info(ctx)

            ctx = self._step2_get_new_trip(ctx)
            ctx = self._step3_get_payment_key(ctx)
            ctx = self._step4_get_new_price(ctx)
            ctx = self._step2_get_new_trip(ctx,retune=True)
            ctx = self._step3_get_payment_key(ctx,retune=True)
            ctx = self._step4_get_new_price(ctx,retune=True)
            # print(ctx)
        except QuotationError:
            raise
        except Exception as e:
            raise QuotationError(
                f"Quotation flow failed for PNR={request.pnr}: {e}"
            ) from e

        
        
        return build_change_result(ctx)

    # ------------------------------------------------------------------
    # Private: Step Implementations
    # ------------------------------------------------------------------

    def _step1_get_pnr_info(self, ctx: LegQuotationContext) -> LegQuotationContext:
        """
        STEP 1: Fetch PNR info.
        Uses in-memory cache to avoid duplicate API calls for same PNR.
        """
        req = ctx.change_request
        pnr = req.pnr

        

        logger.debug(f"[step1] Fetching PNR info: {pnr}")
        result = self._api.getinfopnr(pnr)

        reservation_key = result.get("reservation_key")
        journey=result.get("journey_info")
        passengers= result.get("passengers")
        
        if not reservation_key:
            raise QuotationError(
                f"getinfopnr did not return reservation_key for PNR={pnr}"
            )
        
        

        # self._pnr_cache[pnr] = pnr_info
        # ctx.pnr_info = pnr_info
        # logger.debug(f"[step1] reservation_key={reservation_key}")
        # logger.debug(f"[step1] journey={passengers}")

        
        departure_journey = JourneyInfo(
            journey_key=journey[0]["journeykey"],
            booking_key=journey[0]["segments"][0]["arrivalAirport"]["Code"],
            origin=journey[0]["segments"][0]["arrivalAirport"]["Code"],
            destination=journey[0]["segments"][0]["departureAirport"]["Code"],
            departure_date=journey[0]["segments"][0]["ETDLocal"],
            flight_no=journey[0]["segments"][0]["Number"],
        )
        return_journey = None
        if len(journey) >1:
            return_journey = JourneyInfo(
                journey_key=journey[1]["journeykey"],
                booking_key=journey[1]["segments"][0]["arrivalAirport"]["Code"],
                origin=journey[1]["segments"][0]["arrivalAirport"]["Code"],
                destination=journey[1]["segments"][0]["departureAirport"]["Code"],
                departure_date=journey[1]["segments"][0]["ETDLocal"],
                flight_no=journey[1]["segments"][0]["Number"]
            )


        ctx.passengers = PassengersQuatity(
            adt=passengers["adt"],
            chd=passengers["chd"],
            inf=passengers["inf"]
        )
        ctx.pnr_info = PnrInfo(
            pnr=pnr,
            reservation_key=reservation_key,
            raw_response="result",
            departure_journey=departure_journey,
            return_journey=return_journey
        )
        

        return ctx

    def _step2_get_new_trip(self, ctx: LegQuotationContext , retune =  False ) -> LegQuotationContext:
        """STEP 2: Get new trip options for the desired change."""
        req = ctx.change_request
        pnr_info = ctx.pnr_info
        assert pnr_info is not None
        if retune or req.segdel == 2 :          #nếu đổi chiều về
            journey=pnr_info.return_journey

        else :
            journey=pnr_info.departure_journey
        # Select correct journey for this leg
        

        if not journey:
            raise QuotationError(
                
                f"No journey found in PNR={req.pnr}"
            )

        # logger.debug(
        #     f"[step2] getnewtrip | {req.dep}→{req.arr} | "
        #     f"old_booking_key={journey.booking_key}"
        # )

        passengers = ctx.passengers
        # print(ctx)
        if retune :  #chiều về
            result = self._api.getnewtrip(
                reservation_key=pnr_info.reservation_key,
                old_booking_key=journey.journey_key,
                arr=req.dep,
                dep=req.arr,
                depdate=req.arr_date,
                
                adt=passengers.adt,
                chd=passengers.chd,
                inf=passengers.inf,
                new_flight_no=req.new_flight_arr_no
            )
            # print (result)
            ctx.new_trip_return_option = NewTripOption(
                new_booking_key=result["fareOption"][0]["BookingKey"],
                flight_no=result["segmentOptions"][0]["flight"]["Number"],
                origin=result["segmentOptions"][0]["flight"]["arrivalAirport"]["Code"],
                destination=result["segmentOptions"][0]["flight"]["departureAirport"]["Code"],
                raw_response="result",
                departure_time=result["segmentOptions"][0]["flight"]["ETDLocal"],
                arrival_time=result["segmentOptions"][0]["flight"]["ETDLocal"],
            )
        else:     #chiều đi
            result = self._api.getnewtrip(
                reservation_key=pnr_info.reservation_key,
                old_booking_key=journey.journey_key,
                dep=req.dep,
                arr=req.arr,
                depdate=req.dep_date,
                
                adt=passengers.adt,
                chd=passengers.chd,
                inf=passengers.inf,
                new_flight_no=req.new_flight_no
            )

        
            # print (result)
            ctx.new_trip_option = NewTripOption(
                new_booking_key=result["fareOption"][0]["BookingKey"],
                flight_no=result["segmentOptions"][0]["flight"]["Number"],
                origin=result["segmentOptions"][0]["flight"]["arrivalAirport"]["Code"],
                destination=result["segmentOptions"][0]["flight"]["departureAirport"]["Code"],
                raw_response="result",
                departure_time=result["segmentOptions"][0]["flight"]["ETDLocal"],
                arrival_time=result["segmentOptions"][0]["flight"]["ETDLocal"],
            )
        if not ctx.new_trip_option.new_booking_key:
            raise QuotationError(
                f"getnewtrip did not return new_booking_key | "
                f"PNR={req.pnr} flight={req.new_flight_no}"
            )
        print(ctx)
        
        # logger.debug(f"[step2] new_booking_key={new_booking_key}")
        return ctx

    def _step3_get_payment_key(self, ctx: LegQuotationContext, retune = False) -> LegQuotationContext:
        """STEP 3: Get payment key for the new booking."""
        pnr_info = ctx.pnr_info
        new_trip = ctx.new_trip_return_option if retune else  ctx.new_trip_option
        assert pnr_info and new_trip

        # logger.debug(
        #     f"[step3] getpaymentkey | "
        #     f"newBookingKey={new_trip.new_booking_key}"
        # )

        result = self._api.getpaymentkey(
            reservation_key=pnr_info.reservation_key,
            new_booking_key=new_trip.new_booking_key,
        )
        print(result)
        payment_key = result.get("payment_key")
        if not payment_key:
            raise QuotationError(
                f"getpaymentkey did not return payment_key | "
                f"PNR={ctx.change_request.pnr}"
            )
        if retune:
            ctx.payment_return_info = PaymentInfo(
                payment_key=payment_key,
                raw_response="raw_response",
            )
        else:
            ctx.payment_info = PaymentInfo(
                payment_key=payment_key,
                raw_response="raw_response",
            )
        # logger.debug(f"[step3] payment_key={payment_key}")
        return ctx

    def _step4_get_new_price(self, ctx: LegQuotationContext,retune = False) -> LegQuotationContext:
        """
        STEP 4: Get price quotation.
        READ ONLY — does NOT confirm booking change.
        """
        req = ctx.change_request
        pnr_info = ctx.pnr_info
        
            
        
        new_trip = (
            ctx.new_trip_return_option
            if (retune ==True )
            else ctx.new_trip_option
        )
        payment_info = (
            ctx.payment_return_info
            if (retune ==True )
            else ctx.payment_info
        )
        assert pnr_info and new_trip and payment_info

        # Use original journey_key (not new one — this is the key to quote against)
        journey = (
            pnr_info.return_journey
            if (retune ==True or req.segdel ==2)
            else pnr_info.departure_journey
        )
        assert journey

        logger.debug(
            f"[step4] getnewprice | "
            f"old_journey_key={journey.journey_key} | "
            f"new_booking_key={new_trip.new_booking_key}"
        )

        result = self._api.getnewprice(
            reservation_key=pnr_info.reservation_key,
            old_journey_key=journey.journey_key,
            new_booking_key=new_trip.new_booking_key,
            payment_key=payment_info.payment_key,
        )
        if retune:
            ctx.quotation_return = PriceQuotation(
                
                total_price_change=result.get("total_price_change"),
                fare_difference=result.get("fare_difference"),
                change_fee=result.get("change_fee"),
                reservationCredits=result.get("reservationCredits"),
            )
        else:
            ctx.quotation = PriceQuotation(
                
                total_price_change=result.get("total_price_change"),
                fare_difference=result.get("fare_difference"),
                change_fee=result.get("change_fee"),
                reservationCredits=result.get("reservationCredits"),
            )
        # logger.debug(
        #     f"[step4] total_price_change={ctx.quotation.total_price_change}"
        # )
        return ctx

    # ------------------------------------------------------------------
    # Cache Management
    # ------------------------------------------------------------------
    def pre_change_vj_pnr(self, pnr : str ):
        result = self._api.getinfopnr(pnr)
        result = extract_trips(result["raw_response"]["data"]) 
        return result
    def clear_pnr_cache(self, pnr: str | None = None) -> None:
        """
        Clear PNR cache to avoid stale quotation data.
        Call this if you suspect booking state has changed
        or between separate quotation sessions.

        Args:
            pnr: Specific PNR to clear. Clears all if None.
        """
        if pnr:
            self._pnr_cache.pop(pnr, None)
            logger.debug(f"PNR cache cleared for: {pnr}")
        else:
            self._pnr_cache.clear()
            logger.debug("All PNR cache cleared")
