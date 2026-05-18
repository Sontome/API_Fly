import requests

from mail_queue_service import MailQueueService


API_URL = "http://localhost:8000/call-ticket-all"


def process_missing_pnrs():
    rows = MailQueueService.get_pending_with_missing_pnrs()

    if not rows:
        print("Không có row nào cần xử lý")
        return

    all_pnrs = []

    for row in rows:
        missing_pnrs = row.get("missing_pnrs", [])

        if missing_pnrs and isinstance(missing_pnrs, list):
            all_pnrs.extend(missing_pnrs)

    # remove duplicate
    all_pnrs = list(set(all_pnrs))

    if not all_pnrs:
        print("Không có missing_pnrs")
        return

    # ABC123,ABC456
    pnr_list = ",".join(all_pnrs)

    print(f"Calling API với pnr_list={pnr_list}")

    try:
        response = requests.get(
            API_URL,
            params={
                "pnr_list": pnr_list
            },
            headers={
                "accept": "application/json"
            },
            timeout=60
        )

        print("Status:", response.status_code)
        print("Response:", response.text)

        # update retry_count
        for row in rows:
            current_retry = row.get("retry_count", 0)

            MailQueueService.update(
                queue_id=row["id"],
                data={
                    "retry_count": current_retry + 1
                }
            )

        print(f"Đã update retry_count cho {len(rows)} rows")

    except Exception as e:
        print("Lỗi call API:", str(e))


# if __name__ == "__main__":
#     process_missing_pnrs()