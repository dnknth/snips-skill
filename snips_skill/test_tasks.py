from datetime import datetime, timedelta
from localtime import *
from pprint import pprint
from tasks import Tasks
from unittest.mock import patch
import unittest, time


class TasksTest(unittest.TestCase):

    t1 = Tasks.Task(at(1), 't1', print)
    t2 = Tasks.Task(at(2), 't2', print)
    t3 = Tasks.Task(at(3), 't3', print)
    tasks = (t1, t2, t3) # sorted by time


    def setUp(self):
        self.sut = Tasks(0.01) # speed up for tests


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
        lines = repr(self.sut).split('\n')
        
        self.assertIn(str(self.t1.when), lines[1])
        self.assertIn(str(self.t2.when), lines[2])
        self.assertIn(str(self.t3.when), lines[3])
        
        
    @patch('tasks.now')
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
        self.sut.cancel('t2')
        self.assertNotIn(self.t2, self.sut)
        self.assertIn(self.t1, self.sut)
        self.assertIn(self.t3, self.sut)
        self.assertEqual(2, len(self.sut))


    @patch('tasks.now')
    def test_run(self, clock):            
        output = []
        t1 = Tasks.Task(at(0,1), 't1', lambda: output.append('t1'))
        t2 = Tasks.Task(at(0,2), 't2', lambda: output.append('t2'))
        t3 = Tasks.Task(at(0,3), 't3', lambda: output.append('t3'))        
        self.sut.addAll((t2, t1, t3))
        
        clock.return_value = t3.when
        time.sleep((len(self.sut) + 1) * self.sut.resolution)
        self.assertEqual(['t1', 't2', 't3'], output)
        

if __name__ == '__main__': unittest.main()
