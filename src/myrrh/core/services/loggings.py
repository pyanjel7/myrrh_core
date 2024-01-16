import logging
import logging.config

import re

from .config import cfg_get, cfg_init

log = logging.getLogger("myrrh")

_CONF_OBJ_TYPE = (
    "loggers",
    "handlers",
    "formatters",
    "filters",
)


def configure_log():
    import configparser

    logging_cfg = cfg_get(section="logging")

    cfg = configparser.RawConfigParser()

    for obj_type in _CONF_OBJ_TYPE:
        cfg.add_section(obj_type)
        cfg[obj_type]["keys"] = logging_cfg.get(obj_type) or ""
        keys = filter(None, re.split(" *, *| +| *; *", cfg[obj_type]["keys"]))
        for key in keys:
            obj_name = obj_type.rstrip("s")
            cfg.add_section(f"{obj_name}_{key}")
            for k, v in cfg_get(section=f"logging.{obj_name}.{key}").items():
                cfg[f"{obj_name}_{key}"][k] = v

    logging.config.fileConfig(cfg, disable_existing_loggers=logging_cfg.get("disable_existing_loggers", True))

    if not cfg_get("enable", True, section="logging"):
        logging.disable()


def init_logging_srv():
    import configparser
    from myrrh.core.services.config import cfg_get

    cfg_init("enable", False, section="logging")
    cfg_init("version", 1, section="logging")
    cfg_init("incremental", False, section="logging")
    cfg_init("disable_existing_loggers", True, section="logging")
    cfg_init("loggers", "root, myrrh", section="logging")
    cfg_init("handlers", "console, myrrh", section="logging")
    cfg_init("formatters", "myrrh", section="logging")
    cfg_init("filters", "", section="logging")

    cfg_init("level", "CRITICAL", section="logging.logger.root")
    cfg_init("handlers", "console", section="logging.logger.root")

    cfg_init("level", "INFO", section="logging.logger.myrrh")
    cfg_init("handlers", "myrrh", section="logging.logger.myrrh")
    cfg_init("qualname", "myrrh", section="logging.logger.myrrh")
    cfg_init("propagate", "0", section="logging.logger.myrrh")

    cfg_init("class", "StreamHandler", section="logging.handler.myrrh")
    cfg_init("level", "DEBUG", section="logging.handler.myrrh")
    cfg_init("formatter", "myrrh", section="logging.handler.myrrh")
    cfg_init("args", "(sys.stdout,)", section="logging.handler.myrrh")

    cfg_init("class", "StreamHandler", section="logging.handler.console")
    cfg_init("level", "CRITICAL", section="logging.handler.myrrh")
    cfg_init("args", "(sys.stdout,)", section="logging.handler.myrrh")

    cfg_init(
        "format",
        "%(relativeCreated).1f - %(name)s:%(threadName)s - %(levelname)s - %(message)s",
        section="logging.formatter.myrrh",
    )

    logging_cfg = cfg_get(section="logging")

    cfg = configparser.RawConfigParser()

    for obj_type in _CONF_OBJ_TYPE:
        cfg.add_section(obj_type)
        cfg[obj_type]["keys"] = logging_cfg.get(obj_type) or ""
        keys = filter(None, re.split(" *, *| +| *; *", cfg[obj_type]["keys"]))
        for key in keys:
            obj_name = obj_type.rstrip("s")
            cfg.add_section(f"{obj_name}_{key}")
            for k, v in cfg_get(section=f"logging.{obj_name}.{key}").items():
                cfg[f"{obj_name}_{key}"][k] = v

    logging.config.fileConfig(cfg, disable_existing_loggers=logging_cfg.get("disable_existing_loggers", True))

    if not cfg_get("enable", True, section="logging"):
        logging.disable()
