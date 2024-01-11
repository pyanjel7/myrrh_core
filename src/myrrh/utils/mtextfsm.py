import importlib.resources
import textfsm

_dir = importlib.resources.files("myrrh.resources.textfsm")


def getparser(name):
    with open(_dir / '.'.join((name, "textfsm"))) as f:
        return Context(textfsm.TextFSM(f))


class Context:
    def __init__(self, textfsm):
        self.textfsm = textfsm

    def __enter__(self):
        return self.textfsm

    def __exit__(self, _t, _v, _tb):
        self.textfsm.Reset()
