#!/usr/bin/env python
# -*- coding: utf-8 -*-

from apscheduler.scheduler import Scheduler
import time
import psutil
import logging
import socket, os
#logging.basicConfig()
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
#                    filename=opts.log,
#                    filemode='w'
					)
class ProcessTracker:
	def __init__(self):
		self.pids = {}
		self.pidnames = {}
		self.scheduler = Scheduler()
		self.scheduler.add_interval_job(self.tracking_job, seconds=1)
		self.scheduler.start()
	def track(self, pid, name):
		self.pids[pid] = psutil.Process(int(pid))
		self.pidnames[pid] = name
	def untrack(self, pid):
		try:
			del self.pids[pid]
			del self.pidnames[pid]
		except KeyError:
			logging.warning("PID %s was not tracked" % pid)
	def tracking_job(self):
		print "Tracked pids: %s\n" % ' '.join(self.pids)
		for pid in self.pids.keys():
			self.submit(pid,self.collect(pid))
	def collect(self, pid):
		results = {}
		try:
			p = self.pids[pid]
			results["cpu.pct"] = p.get_cpu_percent(0)
			results["cpu.usr"], results["cpu.sys"] = p.get_cpu_times()
			results["csw.voluntary"], results["csw.involuntary"] = p.get_num_ctx_switches()
		except psutil.NoSuchProcess:
			logging.exception("No such process")
		return results
	def submit(self, pid, results):
		for metric in results.keys():
			logging.info("%s.%s\t%s\t%d" % (self.pidnames[pid], metric, results[metric], time.time()))
def main():
	pt = ProcessTracker()
	pt.track('5822', 'process1')
	pt.track('425', 'process2')
	s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
	try:
		os.remove("/tmp/socketname")
	except OSError:
		pass
	s.bind("/tmp/socketname")
	s.listen(1)
	conn, addr = s.accept()
	while 1:
		data = conn.recv(1024)
		if not data: break
		# TODO: better cmd parser logic
		command, pid, name = data.split(' ')
		if command == 'track':
			pt.track(pid, name)
		if command == 'untrack':
			pt.untrack(pid)
	conn.close()

if __name__ == "__main__":
  main()

