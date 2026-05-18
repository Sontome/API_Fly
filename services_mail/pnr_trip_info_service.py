from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(url, key)

TABLE_NAME = "ticket_log"


class PnrTripInfoService:

    # READ latest row by pnr
    @staticmethod
    def get_latest_by_pnr(pnr: str):

        response = (
            supabase.table(TABLE_NAME)
            .select("*")
            .eq("pnr", pnr)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if response.data and len(response.data) > 0:
            return response.data[0]

        return None
# print(PnrTripInfoService.get_latest_by_pnr("FVSUGR"))