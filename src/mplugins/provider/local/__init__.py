import os
import typing

import myrrh
from myrrh.core.interfaces.ieservices import IEService

import myrrh.warehouse.utils
import myrrh.warehouse.items
import myrrh.provider


from .system import Shell, Stream, FileSystem, StreamSystemAPI
from .vendor import Warehouse

__version__ = myrrh.__version__


class LocalProviderSettings(myrrh.warehouse.items.Settings):
    name: typing.Literal["local"]
    cwd: str | None = None


class LocalProvider(myrrh.provider.IProvider, _name_="local"):
    """
    Local tools commands
    """

    def __init__(self, settings=None):
        """
        instantiate specific local services
        """
        if settings and settings.cwd:
            cwd = os.path.expandvars(settings.cwd)
            cwd = os.path.expanduser(cwd)
            os.chdir(cwd)

    def services(self):
        return (Stream, Shell, FileSystem, StreamSystemAPI, Warehouse)

    def subscribe(self, serv: type[IEService]) -> IEService | None:
        return serv()


Provider = LocalProvider
ProviderSettings = LocalProviderSettings
