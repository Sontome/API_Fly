from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

from pnr_trip_info_service import (
    PnrTripInfoService
)

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(url, key)

TABLE_NAME = "pnr_email_logs"


class LogMailQueueService:

    # CREATE
    @staticmethod
    def create(
        pnr: str,
        email: str,
        mail_type: int,
        customer_name: str = None,
        salutation: str = None,
        phone: str = None,
    ):

        # lấy trip info mới nhất
        trip_info = (
            PnrTripInfoService
            .get_latest_by_pnr(pnr)
        )

        data = {
            "pnr": pnr,
            "email": email,
            "customer_name": customer_name,
            "salutation": salutation,
            "mail_type": mail_type,
            "phone": phone,

            "trip1": None,
            "day1": None,
            "time1": None,

            "trip2": None,
            "day2": None,
            "time2": None,

            "trip3": None,
            "day3": None,
            "time3": None,

            "trip4": None,
            "day4": None,
            "time4": None,

            "first_sent_at": datetime.now(
                timezone.utc
            ).isoformat(),

            "last_sent_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        # nếu có trip info thì map data
        if trip_info:

            data.update({

                "trip1": trip_info.get("trip1"),
                "day1": trip_info.get("day1"),
                "time1": trip_info.get("time1"),

                "trip2": trip_info.get("trip2"),
                "day2": trip_info.get("day2"),
                "time2": trip_info.get("time2"),

                "trip3": trip_info.get("trip3"),
                "day3": trip_info.get("day3"),
                "time3": trip_info.get("time3"),

                "trip4": trip_info.get("trip4"),
                "day4": trip_info.get("day4"),
                "time4": trip_info.get("time4"),
            })

        response = (
            supabase.table(TABLE_NAME)
            .insert(data)
            .execute()
        )

        return response.data
LogMailQueueService.create(
    pnr="ABC123",
    email="test@gmail.com",
    customer_name="Sơn",
    salutation="Anh",
    phone="0123456789",
    mail_type="ticket"
)