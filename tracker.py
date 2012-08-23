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
                    filename='stats.log',
                    filemode='w'
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
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.bind(("0.0.0.0",6666))
	s.listen(1)
	conn, addr = s.accept()
	while 1:
		data = conn.recv(1024)
		if not data: break
		# TODO: better cmd parser logic
		try:
			command, pid, name = data.rstrip('\r\n').split(' ')
			if command == 'track':
				pt.track(pid, name)
				conn.sendall('OK\n')
			elif command == 'untrack':
				pt.untrack(pid)
				conn.sendall('OK %s\n' % data.rstrip('\r\n'))
			else:
				conn.sendall('FAIL %s\n' % data.rstrip('\r\n'))
		except ValueError:
			conn.sendall('FAIL %s\n**USAGE:\n\ttrack <pid> <key> -- to start tracking pid\n\tuntrack <pid> -- to stop tracking pid\n' % data.rstrip('\r\n'))
	conn.close()

if __name__ == "__main__":
  main()

