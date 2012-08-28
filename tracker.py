#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Process tracking utility. Collects resource infromation for selected PIDs.
That PIDs can be added or removed dynamically
'''
from apscheduler.scheduler import Scheduler
from optparse import OptionParser
import time
import psutil
import logging
import socket

logging.basicConfig(level=logging.INFO,
                    format=\
                    '%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename='stats.log',
                    filemode='w'
                    )

class Collector(object):
    '''Collects process information by using psutil'''
    KEYS = ['num_ctx_switches', \
            'cpu_percent', \
            'cpu_times', \
            'io_counters', \
            'num_threads', \
            'memory_percent', \
            'ext_memory_info']
    def __init__(self, pid, name):
        self.process = psutil.Process(int(pid))
        self.name = name
    def collect(self):
        '''
        Returns process information as a dict of metrics
        Agregated (sum) with childs if any.
        '''
        results = [Collector.process_info(process) for process in self.process.get_children(True)]
        results.append(Collector.process_info(self.process))
        return Collector.sum_dicts(results)
    @staticmethod
    def sum_dicts(dicts):
        '''sums dicts by key'''
        return reduce(lambda a, b: dict( (key, a.get(key, 0)+b.get(key, 0)) for key in set(a)|set(b) ), dicts)
    @staticmethod
    def process_info(process):
        '''Returns info for specific process as a dict of metrics'''
        results = {}
        try:
            res_dict = process.as_dict()
            for key in Collector.KEYS:
                if key in res_dict.keys():
                    if type(res_dict[key]) in [float, int]:
                        results[key] = res_dict[key]
                    else:
                        try:
                            metrics = res_dict[key]._asdict()
                        except AttributeError:
                            pass
                        for m_key in metrics.keys():
                            results["%s.%s" % (key, m_key)] = metrics[m_key]
                else:
                    logging.warning("Metric %s not found", key)
        except psutil.NoSuchProcess:
            logging.exception("No such process")
        return results

class TrackerManager(object):
    '''Manages process information collection for multiple processes'''
    def __init__(self):
        self.pids = {}
        self.listeners = []
        self.scheduler = Scheduler()
        self.scheduler.add_interval_job(self.tracking_job, seconds=1)
        self.scheduler.start()
    def add_listener(self, listener):
        '''Add listener that will receive metrics'''
        self.listeners.append(listener)
    def track(self, pid, name):
        '''Start tracking for process, with selected metric sub-name'''
        logging.info("Start tracking for %s/%s", pid, name)
        try:    
            process = Collector(pid, name)
            self.pids[pid] = process
        except psutil.NoSuchProcess:
            logging.exception("No such process")
    def untrack(self, pid):
        '''Stop tracking process (PID == pid)'''
        try:
            logging.info("Stop tracking for %s/%s", pid, self.pids[pid].name)
            del self.pids[pid]
        except KeyError:
            logging.warning("PID %s was not tracked", pid)
    def tracking_job(self):
        '''a job that tracks for processes'''
        logging.debug("Tracked pids: %s\n", ' '.join(self.pids))
        for pid in self.pids.keys():
            self.submit(self.pids[pid].collect())
    def submit(self, results):
        '''publish results to listeners'''
        for listener in self.listeners:
            listener.submit(results)

class LoggerListener(object):
    '''Listener that writes metrics to log'''
    def __init__(self, name):
        self.logger = logging.getLogger(name)
    def submit(self, results):
        '''publish results to log'''
        for metric in results.keys():
            self.logger.info("%s\t%s\t%d" % \
                (metric, results[metric], time.time()))

class GraphiteListener(object):
    '''Listener that writes metrics to Graphite'''
    def __init__(self, prefix, address, port):
        self.address = address
        self.port = port
        self.logger = logging.getLogger("graphite")
        self.prefix = prefix
    def submit(self, results):
        '''publish results to Graphite'''
        # TODO make it send data to graphite
        for metric in results.keys():
            self.logger.info("%s\t%s\t%d" % \
                (metric, results[metric], time.time()))

def parse_options():
    '''parse command line options'''
    argparser = OptionParser()
    argparser.add_option('-p', '--port', 
                        help='a port to listen', 
                        dest='port', 
                        default=6666
                        )
    return argparser.parse_args()

def main():
    '''main function'''
    opts, _ = parse_options()
    t_m = TrackerManager()
    t_m.add_listener(LoggerListener("metrics"))
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("0.0.0.0", opts.port))
    sock.listen(3)
    conn, _ = sock.accept()
    while 1:
        data = conn.recv(4096)
        if not data:
            break
        for line in data.splitlines():
            req = line.rstrip('\r\n')
            try:
                command, pid, name = req.split(' ')
                if command == 'track':
                    t_m.track(pid, name)
                    conn.sendall('OK %s\n' % req)
                elif command == 'untrack':
                    t_m.untrack(pid)
                    conn.sendall('OK %s\n' % req)
                else:
                    conn.sendall('FAIL %s\n' % req)
            except ValueError:
                conn.sendall('FAIL %s\n**USAGE:\n\t\
                    track <pid> <key> -- to start tracking pid\n\t\
                    untrack <pid> <key> -- to stop tracking pid\n' % req)
    conn.close()

if __name__ == "__main__":
    main()
