import asyncio
import inspect
import logging
from asyncio import AbstractEventLoop
from asyncio import Task as _Task
from datetime import datetime, timedelta
from typing import Callable, Optional

import dis_snek
from dis_snek.client.const import logger_name, MISSING
from .triggers import BaseTrigger

log = logging.getLogger(logger_name)


class Task:
    """
    Create an asynchronous background tasks. Tasks allow you to run code according to a trigger object.

    A task's trigger must inherit from `BaseTrigger`.

    """

    callback: Callable
    trigger: BaseTrigger
    task: _Task
    _stop: asyncio.Event
    iteration: int

    def __init__(self, callback: Callable, trigger: BaseTrigger):
        self.callback = callback
        self.trigger = trigger
        self._stop = asyncio.Event()
        self.task = MISSING
        self.iteration = 0

    @property
    def _loop(self) -> AbstractEventLoop:
        return asyncio.get_event_loop()

    @property
    def next_run(self) -> Optional[datetime]:
        """Get the next datetime this task will run."""
        if not self.task.done():
            return self.trigger.next_fire()
        return None

    @property
    def delta_until_run(self) -> Optional[timedelta]:
        if not self.task.done():
            return self.next_run - datetime.now()

    def on_error(self, error):
        dis_snek.Snake.default_error_handler("Task", error)

    async def __call__(self) -> None:
        try:
            if inspect.iscoroutinefunction(self.callback):
                await self.callback()
            else:
                self.callback()
        except Exception as e:
            self.on_error(e)

    def _fire(self, fire_time: datetime):
        """Called when the task is being fired."""
        self.trigger.last_call_time = fire_time
        self._loop.create_task(self())
        self.iteration += 1

    async def _task_loop(self):
        while not self._stop.is_set():
            fire_time = self.trigger.next_fire()
            if fire_time is None:
                return self.stop()

            try:
                await asyncio.wait_for(self._stop.wait(), max(0.0, (fire_time - datetime.now()).total_seconds()))
            except asyncio.TimeoutError:
                pass
            else:
                return

            self._fire(fire_time)

    def start(self) -> None:
        """Start this task."""
        self._stop.clear()
        if self._loop:
            self.task = asyncio.create_task(self._task_loop())

    def stop(self) -> None:
        """End this task."""
        self._stop.set()
        if self.task:
            self.task.cancel()

    def restart(self) -> None:
        """Restart this task."""
        self.stop()
        self.start()

    def reschedule(self, trigger: BaseTrigger) -> None:
        """
        Change the trigger being used by this task.

        Args:
            trigger: The new Trigger to use

        """
        self.trigger = trigger
        self.restart()

    @classmethod
    def create(cls, trigger: BaseTrigger) -> Callable[[Callable], "Task"]:
        """
        A decorator to create a task.

        Args:
            trigger: The trigger to use for this task

        """

        def wrapper(func: Callable) -> "Task":
            return cls(func, trigger)

        return wrapper
