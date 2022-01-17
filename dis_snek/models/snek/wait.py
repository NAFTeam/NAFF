from asyncio import Future
from typing import Coroutine, Callable, Optional


class Wait:
    def __init__(self, event: str, checks: Optional[Callable[..., bool]], future: Future):
        self.event = event
        self.checks = checks
        self.future = future

    def __call__(self, *args, **kwargs) -> bool:
        if self.future.cancelled():
            return True

        if self.checks:
            try:
                check_result = self.checks(*args, **kwargs)
            except Exception as exc:
                self.future.set_exception(exc)
                return True
        else:
            check_result = True

        if check_result:
            self.future.set_result(*args, **kwargs)
            return True

        return False
