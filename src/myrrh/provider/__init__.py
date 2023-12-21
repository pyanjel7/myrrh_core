# flake8: noqa: F403

from ._iprovider import *
from ._iservices import *


def service_fullname(service):
    return f"{service.category}/{service.name}/{str(service.protocol)}"
