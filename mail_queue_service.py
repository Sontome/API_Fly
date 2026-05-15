from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
# print(url)
# print(key)
supabase = create_client(url, key)

TABLE_MAIL_QUEUE = "mail_queue"
TABLE_LOG = "pnr_email_logs"

class MailQueueService:

    # CREATE
    @staticmethod
    def create(
        email: str,
        pnrs: list,
        customer_name: str = None,
        salutation: str = None,
        banner: str = None,
    ):

        data = {
            "email": email,
            "customer_name": customer_name,
            "salutation": salutation,
            "pnrs": pnrs,
            "missing_pnrs": [],
            "status": "pending",
            "retry_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "banner": banner,
        }

        response = (
            supabase.table(TABLE_MAIL_QUEUE)
            .insert(data)
            .execute()
        )

        return response.data
    # READ BY STATUS
    @staticmethod
    def get_by_status(
        status: str,
        limit: int = 100
    ):

        response = (
            supabase.table(TABLE_MAIL_QUEUE)
            .select("*")
            .eq("status", status)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return response.data
    # READ ALL
    @staticmethod
    def get_all():

        response = (
            supabase.table(TABLE_MAIL_QUEUE)
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )

        return response.data

    # READ BY ID
    @staticmethod
    def get_by_id(queue_id: str):

        response = (
            supabase.table(TABLE_MAIL_QUEUE)
            .select("*")
            .eq("id", queue_id)
            .single()
            .execute()
        )

        return response.data

    # UPDATE
    @staticmethod
    def update(
        queue_id: str,
        data: dict
    ):

        data["updated_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        response = (
            supabase.table(TABLE_MAIL_QUEUE)
            .update(data)
            .eq("id", queue_id)
            .execute()
        )

        return response.data

    # DELETE
    @staticmethod
    def delete(queue_id: str):

        response = (
            supabase.table(TABLE_MAIL_QUEUE)
            .delete()
            .eq("id", queue_id)
            .execute()
        )

        return response.data
class PnrEmailLogsService:

    # CREATE
    @staticmethod
    def create(
        pnr: str,
        email: str,
        customer_name: str = None,
        salutation: str = None,
        mail_type: str = "ticket",
    ):

        now = datetime.now(
            timezone.utc
        ).isoformat()

        data = {
            "pnr": pnr,
            "email": email,
            "customer_name": customer_name,
            "salutation": salutation,
            "mail_type": mail_type,
            "first_sent_at": now,
            "last_sent_at": now,
            "send_count": 1,
        }

        response = (
            supabase.table(TABLE_LOG)
            .upsert(
                data,
                on_conflict="pnr,email,mail_type"
            )
            .execute()
        )

        return response.data
# MailQueueService.create(
#     email="test@gmail.com",
#     customer_name="Sơn",
#     salutation="Anh",
#     pnrs=["ABC123", "XYZ999"]
# )
# queues = MailQueueService.get_by_status(
#     "pending"
# )
# print(queues)
# PnrEmailLogsService.create(
#     pnr="ABC123",
#     email="test@gmail.com",
#     customer_name="Sơn",
#     salutation="Anh",
#     mail_type="ticket"
# )
