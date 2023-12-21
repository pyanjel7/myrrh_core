import os
import textfsm

_dir = os.path.dirname(__file__)


def getparser(name):
    with open(os.path.join(_dir, name + ".textfsm")) as f:
        return Context(textfsm.TextFSM(f))


class Context:
    def __init__(self, textfsm):
        self.textfsm = textfsm

    def __enter__(self):
        return self.textfsm

    def __exit__(self, _t, _v, _tb):
        self.textfsm.Reset()
