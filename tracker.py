#!/usr/bin/env python
# -*- coding: utf-8 -*-

from apscheduler.scheduler import Scheduler
import time
import logging
logging.basicConfig()

class ProcessTracker:
	def __init__(self):
		self.pids = set()
		self.scheduler = Scheduler()
		self.scheduler.add_interval_job(self.tracking_job, seconds=1)
		self.scheduler.start()
	def track(self, pid):
		self.pids.add(pid)
	def untrack(self, pid):
		try:
			self.pids.remove(pid)
		except KeyError:
			print "No such pid: %s" % pid
	def tracking_job(self):
		print "Tracked pids: %s\n" % ' '.join(self.pids)
def main():
  pt = ProcessTracker()

  time.sleep(2)
  pt.track('2345')
  time.sleep(3)
  pt.track('2412')
  time.sleep(2)
  pt.untrack('2345')
  time.sleep(2)
  pt.untrack('666')
  time.sleep(2)

if __name__ == "__main__":
  main()

