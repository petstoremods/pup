import signal, sys

signal.signal(signal.SIGINT, lambda num,_: sys.exit(num))
signal.signal(signal.SIGTERM, lambda num,_: sys.exit(num))

