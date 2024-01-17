import importlib
import typing

from myrrh.core.services.plugins import load_ext_group

from ._iprovider import IProvider


class ProviderRegistry:
    providers: dict[str, typing.Type[IProvider]] = {}

    provider_sep = "_"
    provider_prefix = provider_sep.join(("myrrh", "provider"))

    __single__: typing.Optional["ProviderRegistry"] = None

    def __new__(cls):
        if cls.__single__ is None:
            cls.__single__ = super().__new__(cls)
        return cls.__single__

    def __getattr__(self, name) -> typing.Type[IProvider]:
        return self.get(name)

    def get(self, name: str) -> typing.Type[IProvider]:
        try:
            return self.providers[name]
        except KeyError:
            pass

        raise AttributeError(f'{name} is not a valid provider name, available providers: {", ".join(self.providers)}')

    def is_provider_dist(self, dist_name: str) -> bool:
        return len(dist_name) > len(self.provider_prefix) + 1 and dist_name.startswith(self.provider_prefix + self.provider_sep)

    def dist_name(self, provider_name: str) -> str:
        return self.provider_sep.join((self.provider_prefix, provider_name))

    def name_from_dist(self, dist_name: str) -> str:
        if self.is_provider_dist(dist_name):
            return dist_name[len(self.provider_prefix) + 1 :]
        return ""

    def get_version(self, provider_name: str) -> str:
        if provider_name not in self.providers:
            return ""

        provider = self.providers[provider_name]
        # look for __version__.py module inside provider
        try:
            version_module = importlib.import_module(f"{provider.__name__}.__version__")
        except (ModuleNotFoundError, ImportError):
            pass

        version = "0.0.0"
        for attr in ("version", "__version__"):
            try:
                version = getattr(version_module, attr)
                break
            except AttributeError:
                pass

        return version

    def _new_provider(self, provider_cls: typing.Type[IProvider]):
        assert issubclass(provider_cls, IProvider), f"{repr(provider_cls)} is not a valid provider implementation, provider must inherit from IProvider"

        self.providers[provider_cls._name_] = provider_cls

    def register(self, provider_cls):

        self._new_provider(provider_cls)


def register_provider(module: str):
    mod = importlib.import_module(module)
    provider_cls = getattr(mod, "Provider")

    if not isinstance(provider_cls, (list, tuple)):
        provider_cls = [provider_cls]

    for provider in provider_cls:
        ProviderRegistry().register(provider)


load_ext_group("myrrh.provider.registry")
