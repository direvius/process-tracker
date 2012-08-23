process-tracker
===============

Extensible process tracking python script.
Run, connect to TCP 6666 and send:
* ```track <pid> <key>``` to start tracking pid
* ```untrack <pid>``` to stop tracking pid

Needs ```psutil``` and ```apscheduler``` python packages. Tested on python 2.5