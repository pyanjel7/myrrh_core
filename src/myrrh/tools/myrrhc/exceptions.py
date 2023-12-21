# flake8: noqa: F401

from click.exceptions import Exit, Abort, UsageError


class Reboot(RuntimeError):
    pass


class Failure(RuntimeError):
    pass
