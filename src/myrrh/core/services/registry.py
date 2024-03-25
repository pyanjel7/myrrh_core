import importlib


from ..interfaces import ISecretSrv, IConfigSrv


class ServiceRegistry:
    __single__: type["ServiceRegistry"] | None = None

    def __new__(cls):
        if cls.__single__ is None:
            cls.__single__ = super().__new__(cls)
        return cls.__single__

    secrets: dict[str, type[ISecretSrv]] = {}
    configs: dict[str, type[IConfigSrv]] = {}

    def new(self, type, name, *a, **kwa):
        try:
            cls = getattr(self, type)[name]

        except AttributeError:
            raise ValueError(f"unknown service type: {type}") from None

        except KeyError:
            raise ValueError(f"unknown service {name}") from None

        return cls(*a, **kwa)


def _register(module_name: str, service_name: str, type, clsname):
    module = importlib.import_module(module_name)
    service_cls = getattr(module, clsname)
    getattr(ServiceRegistry(), type)[service_name] = service_cls


def register_secret(module_name: str, service_name: str):
    _register(module_name, service_name, "secrets", "SecretSrv")


def register_config(module_name: str, service_name: str):
    _register(module_name, service_name, "configs", "ConfigSrv")
