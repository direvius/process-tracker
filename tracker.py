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
import string 

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
        results = [self._process_info(process) for process in self.process.get_children(True)]
        results.append(self._process_info(self.process))
        return Collector.sum_dicts(results)
    @staticmethod
    def sum_dicts(dicts):
        '''sums dicts by key'''
        return reduce(lambda a, b: dict( (key, a.get(key, 0)+b.get(key, 0)) for key in set(a)|set(b) ), dicts)
    def _process_info(self, process):
        '''Returns info for specific process as a dict of metrics'''
        results = {}
        try:
            res_dict = process.as_dict()
            for key in Collector.KEYS:
                if key in res_dict.keys():
                    if type(res_dict[key]) in [float, int]:
                        results["%s.%s" % (self.name, key)] = res_dict[key]
                    else:
                        try:
                            metrics = res_dict[key]._asdict()
                        except AttributeError:
                            pass
                        for m_key in metrics.keys():
                            results["%s.%s.%s" % (self.name, key, m_key)] = metrics[m_key]
                else:
                    logging.warning("Metric %s not found", key)
        except psutil.NoSuchProcess:
            logging.exception("No such process")
        return results

class TrackerManager(object):
    '''Manages process information collection for multiple processes'''
    def __init__(self, interval):
        self.pids = {}
        self.listeners = []
        self.scheduler = Scheduler()
        self.scheduler.add_interval_job(self.tracking_job, seconds=interval)
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
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.address, int(self.port)))
        for metric in results.keys():
            sock.sendall("%s.%s\t%s\t%d\n" % \
                (self.prefix, metric, results[metric], time.time()))
        sock.close()

def parse_options():
    '''parse command line options'''
    argparser = OptionParser()
    argparser.add_option('-p', '--port', 
                        help='a port to listen', 
                        dest='port', 
                        default='6666'
                        )
    argparser.add_option('-l', '--log', 
                        help='enable logging metrics',
                        action='store_true', 
                        dest='log_enabled', 
                        default=False
                        )
    argparser.add_option('-L', '--log-file', 
                        help='log file', 
                        dest='logfile', 
                        default='stats.log'
                        )
    argparser.add_option('-r', '--graphite-address', 
                        help='graphite server address', 
                        dest='graphite_address', 
                        default='localhost'
                        )
    argparser.add_option('-R', '--graphite-port', 
                        help='graphite server port', 
                        dest='graphite_port', 
                        default='2024'
                        )
    argparser.add_option('-i', '--interval', 
                        help='collection interval in seconds', 
                        dest='interval', 
                        default='5'
                        )
    hostname = socket.gethostname().translate(string.maketrans(".", "_"))
    argparser.add_option('-P', '--graphite-prefix', 
                        help='graphite prefix', 
                        dest='graphite_prefix', 
                        default='five_sec.process-tracker.%s' % hostname
                        )
    argparser.add_option("-g", "--use-graphite",
                  help="report metrics to graphite",
                  action="store_true", 
                  dest="graphite", 
                  default=False
                  )
    return argparser.parse_args()

def main():
    '''main function'''
    opts, _ = parse_options()
    logging.basicConfig(level=logging.INFO,
                format=\
                '%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                datefmt='%m-%d %H:%M',
                filename=opts.logfile,
                filemode='w'
                )
    t_m = TrackerManager(int(opts.interval))
    if(opts.log_enabled):
        t_m.add_listener(LoggerListener("metrics"))
    if opts.graphite:
        t_m.add_listener(GraphiteListener(opts.graphite_prefix, opts.graphite_address, opts.graphite_port))
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("0.0.0.0", int(opts.port)))
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
