import os
import time
import uuid


def new_id() -> uuid.UUID:
    """UUIDv7 (RFC 9562): 48 bit mili-giây + 74 bit ngẫu nhiên ⇒ sắp theo thời gian (DATA-MODEL §1).

    ponytail: tự viết vì Python 3.12 chưa có uuid.uuid7 (có từ 3.14) — đổi sang stdlib khi nâng Python.
    """
    value = (time.time_ns() // 1_000_000) << 80 | int.from_bytes(os.urandom(10)) & ((1 << 80) - 1)
    value = value & ~(0xF << 76) | 0x7 << 76  # version 7
    value = value & ~(0x3 << 62) | 0x2 << 62  # variant RFC 4122
    return uuid.UUID(int=value)
