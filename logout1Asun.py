import os


SIGNAL = "/tmp/logout1asun"


open(
    SIGNAL,
    "w"
).close()


print("✅ Đã gửi lệnh logout cho login1Asun")
