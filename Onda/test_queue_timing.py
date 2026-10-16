import unittest
from queue_timing import QueueTiming,duration_text

class QueueTimingTests(unittest.TestCase):
    def setUp(self):
        self.now=0.0
        self.timer=QueueTiming(lambda:self.now)
    def test_waits_for_a_completed_job_then_estimates_the_queue(self):
        self.assertEqual(self.timer.snapshot(4),(0,None))
        self.timer.set_running(True);self.now=20
        self.assertEqual(self.timer.snapshot(4),(20,None))
        self.timer.record_completion()
        self.assertEqual(self.timer.snapshot(3),(20,60))
        self.now=40;self.timer.record_completion()
        self.assertEqual(self.timer.snapshot(2),(40,40))
    def test_pause_time_is_not_included_and_estimate_resumes(self):
        self.timer.set_running(True);self.now=10;self.timer.record_completion();self.timer.set_running(False)
        self.now=100
        self.assertEqual(self.timer.snapshot(3),(10,None))
        self.timer.set_running(True);self.now=110
        self.assertEqual(self.timer.snapshot(3),(20,60))
    def test_parallel_completions_use_wall_time_without_double_division(self):
        self.timer.set_running(True);self.now=10
        for _ in range(4):self.timer.record_completion()
        self.assertEqual(self.timer.snapshot(8),(10,20))
    def test_adding_or_removing_work_recalculates_remaining_time(self):
        self.timer.set_running(True);self.now=10;self.timer.record_completion()
        self.assertEqual(self.timer.snapshot(9),(10,90))
        self.assertEqual(self.timer.snapshot(1),(10,10))
    def test_empty_reset_finished_and_old_completed_jobs(self):
        self.timer.record_completion()
        self.timer.set_running(True);self.now=10
        self.assertIsNone(self.timer.snapshot(3)[1])
        self.assertEqual(self.timer.snapshot(0),(10,0))
        self.timer.reset();self.now=100
        self.assertEqual(self.timer.snapshot(0,False),(0,None))
    def test_duration_includes_hours_and_clamps_negative_values(self):
        self.assertEqual(duration_text(65),'01:05')
        self.assertEqual(duration_text(3661),'01:01:01')
        self.assertEqual(duration_text(-1),'00:00')

if __name__=='__main__':unittest.main()
