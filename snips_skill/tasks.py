import logging
import os
import threading
import time
from collections import namedtuple
from datetime import datetime, timedelta
from functools import partial, wraps
from heapq import heapify, heappop, heappush
from random import randint
from signal import SIGUSR2, signal
from typing import Callable, Iterable

from croniter import croniter

__all__ = ("cron", "delay", "now", "Scheduler")


def now() -> datetime:
    "Get the current time in the local time zone"
    return datetime.now().astimezone()


class Tasks(Iterable):
    "A synchronised priority queue of scheduled tasks"

    class Task(namedtuple("Task", "when id func")):  # sorted by when
        def __repr__(self):
            return "Task(%s %s)" % (self.when, self.id)

    def __init__(
        self,
        resolution: float = 0.1,
        daemon: bool = False,
        log_level: int = logging.INFO,
    ):
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.setLevel(log_level)
        self.resolution = resolution
        self.tasks: list = []
        self.mutex = threading.Lock()
        self.worker = threading.Thread(target=self.run, daemon=daemon, name="task_list")
        self.worker.start()

    def add(self, value: Task) -> None:
        "Add a task to the queue"
        self.cancel(value.id)
        with self.mutex:
            heappush(self.tasks, value)
            self.log.debug(
                "Added task (%d/%d): %s",
                self.tasks.index(value) + 1,
                len(self.tasks),
                value,
            )

    def create(
        self, func: Callable, when: datetime | None = None, id: str | None = None
    ) -> None:
        "Add a task from parameters"
        self.add(self.Task(when or now(), id or func.__name__, func))

    def addAll(self, tasks: Iterable[Task]) -> None:
        "Add all tasks from an iterable"
        for task in tasks:
            self.add(task)

    def __len__(self) -> int:
        "Number of tasks in the queue"
        return len(self.tasks)

    def __contains__(self, element: object) -> bool:
        "Membership test"
        if type(element) is str:
            return any(task.id == element for task in self.tasks)
        return element in self.tasks

    def __repr__(self) -> str:
        return "--- %d Tasks:\n%s" % (
            len(self),
            "\n".join(
                "%2d: %s" % (n + 1, t)
                for n, t in enumerate(sorted(self.tasks, key=lambda t: (t.when, t.id)))
            ),
        )

    def __iter__(self):
        return self.tasks.__iter__()

    def cancel(self, id: str) -> None:
        "Remove all tasks with the given ID"
        if id not in self:
            return
        with self.mutex:
            for pos in reversed(
                list(p for p, t in enumerate(self.tasks) if t.id == id)
            ):
                task = self.tasks[pos]
                del self.tasks[pos]
                self.log.debug(
                    "Removed task: (%d/%d) %s", pos + 1, len(self.tasks) + 1, task
                )
            heapify(self.tasks)

    def next(self) -> Task | None:
        "Pop the next available task from the queue"
        if not self.tasks:
            return
        with self.mutex:
            if self.tasks[0].when <= now():
                return heappop(self.tasks)

    def run(self) -> None:
        "Execute pending tasks"
        self.log.debug("Starting tasks...")
        self.running = True

        while self.running:
            task = self.next()
            if task:
                self.execute(task)
            else:
                time.sleep(self.resolution)

        self.log.debug("Stopped tasks")

    def execute(self, task: Task) -> None:
        def wrapper():
            try:
                start = now()
                task.func()
                duration = (now() - start).total_seconds()
                self.log.debug("Task %s took %.2fs", task.id, duration)
            except Exception:
                self.log.exception("Error in task: %s", task.id)

        self.log.debug("Executing task: %s", task.id)
        threading.Thread(target=wrapper, name=task.id, daemon=True).start()

    def stop(self) -> None:
        "Stop polling, must be called from the main thread."
        if self.running:
            self.log.debug("Stopping tasks (%d pending)" % len(self))
            self.running = False
            self.worker.join()


class Scheduler:
    "Mixin class for time-based task execution"

    log: logging.Logger
    startup_tasks: set[tuple[datetime, Callable]] = set()

    def run(self) -> None:
        self.log.debug("--- Starting with PID: %d ---", os.getpid())

        self.tasks = Tasks(resolution=1, daemon=True, log_level=self.log.level)
        signal(SIGUSR2, self.dump_tasks)

        for when, method in self.startup_tasks:
            self.tasks.create(partial(method, self), when, method.__name__)

        try:
            super().run()  # pyright: ignore[reportAttributeAccessIssue]
        finally:
            self.tasks.stop()

    def dump_tasks(self, _signal, _frame):
        "List pending tasks"
        print("Pending tasks: %s" % self.tasks)


def delay(minutes: int = 0, seconds: int = 0, randomize: bool = False):
    "Decorator to delay method execution by a given duration"

    def wrapper(method):
        @wraps(method)
        def delayed_task(self):
            secs = 60 * minutes + seconds
            if randomize:
                secs = randint(0, secs)
            self.tasks.create(
                partial(method, self),
                now() + timedelta(seconds=secs),
                "delayed_" + method.__name__,
            )

        return delayed_task

    return wrapper


def cron(schedule: str, log_level: int = logging.DEBUG):
    "Decorator for periodic tasks"
    sequence = croniter(schedule, now())

    def wrapper(method):
        @wraps(method)
        def periodic_task(self):
            if method.__name__ not in self.tasks:
                when = sequence.get_next(datetime)
                while when < now():
                    when = sequence.get_next(datetime)
                self.tasks.create(partial(periodic_task, self), when, method.__name__)
            self.log.log(log_level, "Invoking: %s" % method.__name__)
            method(self)

        Scheduler.startup_tasks.add((sequence.get_next(datetime), periodic_task))
        return periodic_task

    return wrapper
