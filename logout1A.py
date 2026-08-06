import os


SIGNAL = "/tmp/logout1a"


open(
    SIGNAL,
    "w"
).close()


print("✅ Đã gửi lệnh logout cho login1A")
