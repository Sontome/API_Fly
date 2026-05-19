import threading
import time
from send_ticket_worker import process_mail_queue

class MailScheduler:
    def __init__(self, delay=10):
        self.delay = delay

        self.timer = None
        self.lock = threading.Lock()

        self.worker_running = False
        self.retry = False

    def trigger(self):
        with self.lock:
            print("\n[TRIGGER RECEIVED]")

            # Worker đang chạy
            if self.worker_running:
                print("[INFO] Worker running -> retry ON")
                self.retry = True
                return

            # Reset timer cũ
            if self.timer:
                self.timer.cancel()
                print("[INFO] Countdown reset")

            print(f"[INFO] Start countdown {self.delay}s")

            self.timer = threading.Timer(
                self.delay,
                self._run_worker
            )

            self.timer.start()

    def _run_worker(self):
        with self.lock:
            self.worker_running = True
            self.timer = None

        try:
            self.process_mail_queue()

        finally:
            with self.lock:
                self.worker_running = False

                if self.retry:
                    print("[INFO] Retry detected")

                    self.retry = False

                    print(f"[INFO] Restart countdown {self.delay}s")

                    self.timer = threading.Timer(
                        self.delay,
                        self._run_worker
                    )

                    self.timer.start()

    
