import warnings

from .config import init_local_config_srv, rebase

from .plugins import init_pluggin_srv, load_ext_group
from .loggings import init_logging_srv


def init():
    #
    init_local_config_srv()

    init_pluggin_srv()
    load_ext_group("myrrh.core.services.registry", kind="register_config")

    try:
        rebase()
    except Exception as e:
        warnings.warn(f"unable to rebase config, use default: {str(e)}")

    load_ext_group("myrrh.core.services.registry")

    init_logging_srv()

    # other services should be initialized by module itself

init()
