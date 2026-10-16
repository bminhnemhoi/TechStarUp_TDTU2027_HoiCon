"""Hạn mức theo khóa (id thiết bị) trong cửa sổ trượt, giữ trong bộ nhớ tiến trình (ADR-002: một tiến trình). Bộ nhớ có
trần: đầy thì dọn khóa đã yên rồi mới bỏ khóa cũ nhất, nên một nguồn không thể làm phình bộ nhớ."""

import time
from collections import deque
from uuid import UUID


class SlidingWindowLimit:
    def __init__(self, limit: int, window_s: float, max_tracked: int = 4096) -> None:
        self.limit = limit
        self.window_s = window_s
        self.max_tracked = max_tracked
        self._hits: dict[UUID, deque[float]] = {}

    def reset(self) -> None:
        self._hits.clear()

    def retry_after(self, key: UUID, now: float | None = None) -> int | None:
        """Ghi nhận một lần gọi ⇒ số giây phải đợi nếu đã quá hạn mức, None nếu được nhận."""
        moment = time.monotonic() if now is None else now
        if key not in self._hits and len(self._hits) >= self.max_tracked:
            for stale in [k for k, w in self._hits.items() if not w or moment - w[-1] >= self.window_s]:
                del self._hits[stale]
        if key not in self._hits and len(self._hits) >= self.max_tracked:
            del self._hits[next(iter(self._hits))]
        window = self._hits.setdefault(key, deque())
        while window and moment - window[0] >= self.window_s:
            window.popleft()
        if len(window) >= self.limit:
            return max(1, int(self.window_s - (moment - window[0])))
        window.append(moment)
        return None
