#!/usr/bin/env python
# -*- coding: utf-8 -*-

from apscheduler.scheduler import Scheduler
import time
import psutil
import logging
logging.basicConfig()

class ProcessTracker:
	def __init__(self):
		self.pids = {}
		self.scheduler = Scheduler()
		self.scheduler.add_interval_job(self.tracking_job, seconds=1)
		self.scheduler.start()
	def track(self, pid):
		self.pids[pid] = psutil.Process(int(pid))
	def untrack(self, pid):
		try:
			del self.pids[pid]
		except KeyError:
			print "No such pid: %s" % pid
	def tracking_job(self):
		print "Tracked pids: %s\n" % ' '.join(self.pids)
		for pid in self.pids.keys():
			try:
				print "Pid %s: %f cpu" % (pid, self.pids[pid].get_cpu_percent(0))
			except psutil.NoSuchProcess:
				print "No such process: %s" % pid
def main():
  pt = ProcessTracker()

  time.sleep(2)
  pt.track('5822')
  time.sleep(3)
  pt.track('11024')
  time.sleep(2)
  pt.untrack('5822')
  time.sleep(2)
  pt.untrack('666')
  time.sleep(2)

if __name__ == "__main__":
  main()

