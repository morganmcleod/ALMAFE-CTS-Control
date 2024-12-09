import threading, time, traceback

class Sampler():
    def __init__(self, interval, function, *args, **kwargs):
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.stop_now = False
        self.running = False
        self.thread = None

    def start(self, on_thread: bool = True):
        if on_thread:
            self.thread = threading.Thread(target = self._start)
            self.thread.start()
        else:
            self._start()

    def _start(self):
        self.stop_now = False
        self.running = True
        next_time = time.monotonic() + self.interval
        while not self.stop_now:
            try:
                self.function(*self.args, **self.kwargs)
            except Exception:
                traceback.print_exc()
            time.sleep(max(0, next_time - time.monotonic()))
            next_time += (time.monotonic() - next_time) // self.interval * self.interval + self.interval
        self.running = False
        
    def stop(self):
        self.stop_now = True
        if self.thread:
            self.thread.join()
        self.thread = None
        while self.running:
            time.sleep(0.1)
