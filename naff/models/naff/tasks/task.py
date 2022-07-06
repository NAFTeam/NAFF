import asyncio
import inspect
from asyncio import Task as _Task
from datetime import datetime, timedelta
from typing import Callable, Optional

import naff
from naff.client.const import logger, MISSING
from .triggers import BaseTrigger


__all__ = ("Task",)


class Task:
    """
    Create an asynchronous background tasks. Tasks allow you to run code according to a trigger object.

    A task's trigger must inherit from `BaseTrigger`.

    Attributes:
        callback (Callable): The function to be called when the trigger is triggered.
        trigger (BaseTrigger): The trigger object that determines when the task should run.
        task (Optional[_Task]): The task object that is running the trigger loop.
        iteration (int): The number of times the task has run.

    """

    callback: Callable
    trigger: BaseTrigger
    task: _Task
    _stop: asyncio.Event
    iteration: int

    def __init__(self, callback: Callable, trigger: BaseTrigger) -> None:
        self.callback = callback
        self.trigger = trigger
        self._stop = asyncio.Event()
        self.task = MISSING
        self.iteration = 0

    @property
    def next_run(self) -> Optional[datetime]:
        """Get the next datetime this task will run."""
        if not self.task.done():
            return self.trigger.next_fire()
        return None

    @property
    def delta_until_run(self) -> Optional[timedelta]:
        """Get the time until the next run of this task."""
        if not self.task.done():
            return self.next_run - datetime.now()

    def on_error(self, error: Exception) -> None:
        """Error handler for this task. Called when an exception is raised during execution of the task."""
        naff.Client.default_error_handler("Task", error)

    async def __call__(self) -> None:
        try:
            if inspect.iscoroutinefunction(self.callback):
                await self.callback()
            else:
                self.callback()
        except Exception as e:
            self.on_error(e)

    def _fire(self, fire_time: datetime) -> None:
        """Called when the task is being fired."""
        self.trigger.last_call_time = fire_time
        asyncio.create_task(self())
        self.iteration += 1

    async def _task_loop(self) -> None:
        """The main task loop to fire the task at the specified time based on triggers configured."""
        while not self._stop.is_set():
            fire_time = self.trigger.next_fire()
            if fire_time is None:
                return self.stop()

            try:
                await asyncio.wait_for(self._stop.wait(), max(0.0, (fire_time - datetime.now()).total_seconds()))
            except asyncio.TimeoutError:
                pass
            else:
                return None

            self._fire(fire_time)

    def start(self) -> None:
        """Start this task."""
        try:
            self._stop.clear()
            self.task = asyncio.create_task(self._task_loop())
        except RuntimeError:
            logger.error(
                "Unable to start task without a running event loop! We recommend starting tasks within an `on_startup` event."
            )

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
