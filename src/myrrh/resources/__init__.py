import os

_dirname = os.path.dirname(__file__)


def gettextresource(file, resource=""):
    with open(os.path.join(_dirname, resource, file)) as f:
        return f.read()
