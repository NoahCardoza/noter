import requests
import demjson
from threading import Thread


class ThreadWithReturnValue(Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs={}, Verbose=None):
        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None

    def run(self):
        if self._target is not None:
            self._return = self._target(*self._args,
                                        **self._kwargs)

    def join(self, *args):
        Thread.join(self, *args)
        return self._return


def get_session():
    s = requests.Session()
    s.headers.update({
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36'
    })
    return s


def get_w3_info(res):
    title = res.text.split('<h3>')[1].split('</h3>')[0].strip()
    config = demjson.decode(res.text.split('.setup(')[1].split(');')[0])
    return (title, config)
