import signal

def on_kill(callback):
    signal.signal(signal.SIGINT, lambda num,_: callback())
    signal.signal(signal.SIGTERM, lambda num,_: callback())

