# Tasks
As you develop your bot, you're eventually going to want something to run in the background periodically.
Snek comes with built-in utilities to handle this for you.
___

## Rundown

Creating a task, is really simple. For example, lets say we want something to run every 30 seconds:


```python
from dis_snek.tasks.task import Task
from dis_snek.tasks.triggers import IntervalTrigger

@Task.create(IntervalTrigger(seconds=30))
async def some_task():
    print("A task is running")
```
To start this task, just run `some_task.start()`.

Triggers are used to determine when a task should run, above is an `IntervalTrigger` that triggers the task
at a set interval. Other built-in Triggers can be seen [below](#triggers).

You can also use multiple triggers on one task, lets say you want a task to run every 24 hours and **also** run at 6 am every day:
```python
from dis_snek.tasks.task import Task
from dis_snek.tasks.triggers import IntervalTrigger, TimeTrigger

@Task.create(IntervalTrigger(hours=24) | TimeTrigger(hour=6))
async def some_task():
    print("Time to run!")
```

## API Reference

::: dis_snek.tasks.task

___
## Triggers:


::: dis_snek.tasks.triggers
