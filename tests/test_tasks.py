import logging
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from snips_skill.tasks import Scheduler, Tasks, cron, delay


def at(hour, minute=0):
    "Create a fixed instant in local time"
    return datetime(2020, 1, 1, hour, minute).astimezone()


class TasksTest(unittest.TestCase):
    sut: Tasks

    t1 = Tasks.Task(at(1), "t1", print)
    t2 = Tasks.Task(at(2), "t2", print)
    t3 = Tasks.Task(at(3), "t3", print)
    tasks = (t1, t2, t3)  # sorted by time

    def setUp(self):
        self.sut = Tasks(0.01)  # speed up for tests

    def tearDown(self):
        self.sut.stop()

    def test_add(self):
        self.sut.add(self.t1)
        self.assertIn(self.t1, self.sut)
        self.assertEqual(1, len(self.sut))

        self.sut.add(self.t1)
        self.assertIn(self.t1, self.sut)
        self.assertEqual(1, len(self.sut))

        self.sut.add(self.t2)
        self.assertIn(self.t2, self.sut)
        self.assertEqual(2, len(self.sut))

    def test_repr(self):
        self.sut.addAll(self.tasks)
        lines = repr(self.sut).split("\n")

        self.assertIn(str(self.t1.when), lines[1])
        self.assertIn(str(self.t2.when), lines[2])
        self.assertIn(str(self.t3.when), lines[3])

    @patch("snips_skill.tasks.now")
    def test_next(self, clock):
        self.sut.resolution = 0.1
        time.sleep(0.015)
        self.sut.addAll((self.t3, self.t1, self.t2))

        for expected in self.tasks:
            clock.return_value = expected.when
            task = self.sut.next()

            self.assertIsNotNone(task)
            self.assertEqual(expected, task)
            self.assertNotIn(task, self.sut)
            self.sut.resolution = 0.01

    def test_cancel(self):
        self.sut.addAll(self.tasks)
        self.sut.cancel("t2")
        self.assertNotIn(self.t2, self.sut)
        self.assertIn(self.t1, self.sut)
        self.assertIn(self.t3, self.sut)
        self.assertEqual(2, len(self.sut))

    @patch("snips_skill.tasks.now")
    def test_run(self, clock):
        output = []
        t1 = Tasks.Task(at(0, 1), "t1", lambda: output.append("t1"))
        t2 = Tasks.Task(at(0, 2), "t2", lambda: output.append("t2"))
        t3 = Tasks.Task(at(0, 3), "t3", lambda: output.append("t3"))
        self.sut.addAll((t2, t1, t3))

        clock.return_value = t3.when
        time.sleep((len(self.sut) + 1) * self.sut.resolution)
        self.assertEqual(["t1", "t2", "t3"], output)


class StubTasks:
    "Record task creations instead of running a worker"

    def __init__(self):
        self.created = []
        self.ids = set()

    def __contains__(self, id):
        return id in self.ids

    def create(self, func, when, id):
        self.created.append((func, when, id))
        self.ids.add(id)


class DelayHandler:
    def __init__(self):
        self.tasks = StubTasks()
        self.calls = 0

    @delay(seconds=5)
    def go(self):
        self.calls += 1


class DelayTest(unittest.TestCase):
    def setUp(self):
        self.handler = DelayHandler()

    @patch("snips_skill.tasks.now")
    def test_schedules_future_task(self, clock):
        clock.return_value = at(0)
        self.handler.go()

        self.assertEqual(self.handler.calls, 0)  # deferred, not invoked
        self.assertEqual(len(self.handler.tasks.created), 1)
        when = self.handler.tasks.created[0][1]
        self.assertEqual(when - clock.return_value, timedelta(seconds=5))
        self.assertEqual(self.handler.tasks.created[0][2], "delayed_go")

    @patch("snips_skill.tasks.now")
    def test_minutes_are_converted(self, clock):
        class MinHandler:
            def __init__(self):
                self.tasks = StubTasks()

            @delay(minutes=1)
            def go(self):
                pass

        handler = MinHandler()
        clock.return_value = at(0)
        handler.go()

        when = handler.tasks.created[0][1]
        self.assertEqual(when - clock.return_value, timedelta(minutes=1))

    @patch("snips_skill.tasks.now")
    def test_randomize_bounds(self, clock):
        class RandHandler:
            def __init__(self):
                self.tasks = StubTasks()

            @delay(seconds=10, randomize=True)
            def go(self):
                pass

        handler = RandHandler()
        clock.return_value = at(0)
        handler.go()

        when = handler.tasks.created[0][1]
        delta = when - clock.return_value
        self.assertGreaterEqual(delta, timedelta(0))
        self.assertLessEqual(delta, timedelta(seconds=10))


class CronTest(unittest.TestCase):
    def setUp(self):
        Scheduler.startup_tasks.clear()

    def tearDown(self):
        Scheduler.startup_tasks.clear()

    def test_schedules_once_and_invokes(self):
        class Handler:
            def __init__(self):
                self.tasks = StubTasks()
                self.log = logging.getLogger("test")
                self.calls = 0

            @cron("* * * * *")
            def tick(self):
                self.calls += 1

        handler = Handler()
        handler.tick()

        self.assertEqual(handler.calls, 1)
        self.assertEqual(len(handler.tasks.created), 1)
        self.assertEqual(handler.tasks.created[0][2], "tick")

        handler.tick()
        self.assertEqual(handler.calls, 2)
        self.assertEqual(len(handler.tasks.created), 1)  # no duplicate scheduling

    def test_registers_startup_task(self):
        class Handler:
            def __init__(self):
                self.tasks = StubTasks()
                self.log = logging.getLogger("test")

            @cron("0 * * * *")
            def tick(self):
                pass

        self.assertEqual(len(Scheduler.startup_tasks), 1)
        when, method = next(iter(Scheduler.startup_tasks))
        self.assertIsInstance(when, datetime)
        self.assertTrue(callable(method))


class FakeTasks:
    def __init__(self, resolution, daemon, log_level):
        self.created = []

    def create(self, func, when, id):
        self.created.append((func, when, id))

    def stop(self):
        pass


class Base:
    def run(self):
        pass


class App(Scheduler, Base):
    def __init__(self):
        self.log = logging.getLogger("test")
        self.startup_tasks = set()  # pyright: ignore


class SchedulerTest(unittest.TestCase):
    def test_run_creates_startup_tasks(self):
        app = App()
        app.startup_tasks = {  # pyright: ignore
            (at(1), print),
            (at(2), print),
        }

        with patch("snips_skill.tasks.Tasks", FakeTasks):
            app.run()

        ids = [task[2] for task in app.tasks.created]  # pyright: ignore
        self.assertEqual(len(app.tasks.created), 2)  # pyright: ignore
        self.assertIn("print", ids)


if __name__ == "__main__":
    unittest.main()
