from myrrh.core.services import load_ext_group
from . import _mlib


def register_package(path, name):
    _mlib.__finder__.packages[name] = path


load_ext_group("myrrh.framework.mlib")
