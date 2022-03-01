from asyncio import Event
from typing import Callable, Optional

__all__ = ["Wait"]


class Wait:
    def __init__(self, event: str, checks: Optional[Callable[..., bool]], future: Event):
        self.event = event
        self.checks = checks
        self.future = future

    def __call__(self, *args, **kwargs) -> bool:
        if self.future.is_set():
            return True

        if self.checks:
            try:
                check_result = self.checks(*args, **kwargs)
            except Exception:
                return True
        else:
            check_result = True

        if check_result:
            self.future.set()
            return True

        return False
