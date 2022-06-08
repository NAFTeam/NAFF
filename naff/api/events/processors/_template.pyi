from typing import Callable, Coroutine

from naff import Client
from naff.client.const import Absent

class Processor:
    callback: Coroutine
    event_name: str
    def __init__(self, callback: Coroutine, name: str) -> None: ...
    @classmethod
    def define(cls, event_name: Absent[str] = ...) -> Callable[[Coroutine], "Processor"]: ...

class EventMixinTemplate(Client):
    def __init__(self) -> None: ...
