process-tracker
===============

Extensible process tracking utility. Process resource usage is collected via '''psutil''' and reported to logfile and/or Graphite server (http://graphite.wikidot.com/). Child processes resources are added to it's parent process (wich is tracked).
Run as a service with init.d, connect to TCP 6666 and send:
* ```track <pid> <key>``` to start tracking pid
* ```untrack <pid> <key>``` to stop tracking pid

Needs ```psutil```, ```python-daemon``` and ```apscheduler``` python packages. Don't forget to install them before running the service. Tested on python 2.5.2

Usage: tracker.py [options]

Options:
```
  -h, --help            show this help message and exit
  -p PORT, --port=PORT  a port to listen
  -l, --log             enable logging metrics
  -L LOGFILE, --log-file=LOGFILE
                        log file
  -r GRAPHITE_ADDRESS, --graphite-address=GRAPHITE_ADDRESS
                        graphite server address
  -R GRAPHITE_PORT, --graphite-port=GRAPHITE_PORT
                        graphite server port
  -i INTERVAL, --interval=INTERVAL
                        collection interval in seconds
  -P GRAPHITE_PREFIX, --graphite-prefix=GRAPHITE_PREFIX
                        graphite prefix
  -g, --use-graphite    report metrics to graphite
  -v, --version         show version and exit
```