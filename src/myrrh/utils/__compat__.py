import sys

if sys.version_info.major != 3 or sys.version_info.minor < 10:
    raise RuntimeError("python version not supported")
