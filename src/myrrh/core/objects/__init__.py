# flake8: noqa: F401
from ._entity import *
from ._registry import *

from ..services.config import cfg_init

cfg_init("eid_prefix", "entity", section="myrrh.core.entity")
cfg_init("validate_service_args", True, section="myrrh.core.entity")
