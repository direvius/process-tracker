#!/usr/bin/env python
# -*- coding: utf-8 -*-

from apscheduler.scheduler import Scheduler
from optparse import OptionParser
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
	def __init__(self, pid, name):
		self.process = psutil.Process(int(pid))
		self.name = name
	def collect(self):
		results = {}
		try:
			p = self.process
			#results["%s.cpu.pct"%self.name] = p.get_cpu_percent(0)
			results["%s.cpu.usr"%self.name], results["%s.cpu.sys"%self.name] = p.get_cpu_times()
			results["%s.csw.voluntary"%self.name], results["%s.csw.involuntary"%self.name] = p.get_num_ctx_switches()
		except psutil.NoSuchProcess:
			logging.exception("No such process")
		return results
class TrackerManager:
	def __init__(self):
		self.pids = {}
		self.listeners = []
		self.scheduler = Scheduler()
		self.scheduler.add_interval_job(self.tracking_job, seconds=1)
		self.scheduler.start()
	def add_listener(self, listener):
		self.listeners.append(listener)
	def track(self, pid, name):
		logging.info("Start tracking for %s/%s", pid, name)
		self.pids[pid] = ProcessTracker(pid, name)
	def untrack(self, pid):
		try:
			logging.info("Stop tracking for %s/%s", pid, self.pids[pid].name)
			del self.pids[pid]
		except KeyError:
			logging.warning("PID %s was not tracked" % pid)
	def tracking_job(self):
		logging.debug("Tracked pids: %s\n" % ' '.join(self.pids))
		for pid in self.pids.keys():
			self.submit(self.pids[pid].collect())
	def submit(self, results):
		for listener in self.listeners:
			listener.submit(results)

class LoggerListener:
	def __init__(self, name):
		self.logger = logging.getLogger(name)
	def submit(self, results):
		for metric in results.keys():
			self.logger.info("%s\t%s\t%d" % (metric, results[metric], time.time()))

class GraphiteListener:
	def __init__(self, prefix, address, port):
		self.logger = logging.getLogger("graphite")
		self.prefix = prefix
	def submit(self, results):
		# TODO make it send data to graphite
		for metric in results.keys():
			self.logger.info("%s\t%s\t%d" % (metric, results[metric], time.time()))

def parse_options():
	argparser = OptionParser()
	argparser.add_option('-p', '--port', help='a port to listen', dest='port', default=6666)
	return argparser.parse_args()
def main():
	(opts, args) = parse_options()
	tm = TrackerManager()
	tm.add_listener(LoggerListener("metrics"))
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.bind(("0.0.0.0",opts.port))
	s.listen(3)
	conn, addr = s.accept()
	while 1:
		data = conn.recv(4096)
		if not data: break
		for line in data.splitlines():
			req = line.rstrip('\r\n')
			try:
				command, pid, name = req.split(' ')
				if command == 'track':
					tm.track(pid, name)
					conn.sendall('OK\n')
				elif command == 'untrack':
					tm.untrack(pid)
					conn.sendall('OK %s\n' % req)
				else:
					conn.sendall('FAIL %s\n' % req)
			except ValueError:
				conn.sendall('FAIL (%s)\n**USAGE:\n\ttrack <pid> <key> -- to start tracking pid\n\tuntrack <pid> <key> -- to stop tracking pid\n' % req)
	conn.close()
if __name__ == "__main__":
	main()
