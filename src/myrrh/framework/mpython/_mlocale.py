from myrrh.core.interfaces import abstractmethod
from myrrh.core.services.system import AbcRuntimeDelegate

__mlib__ = "Abc_Locale"


class Abc_Locale(AbcRuntimeDelegate):
    __frameworkpath__ = "mpython._mlocale"

    __all__ = [
        "getlocale",
        "getdefaultlocale",
        "getpreferredencoding",
        "Error",
        "setlocale",
        "resetlocale",
        "localeconv",
        "strcoll",
        "strxfrm",
        "str",
        "atof",
        "atoi",
        "format",
        "format_string",
        "currency",
        "normalize",
        "LC_CTYPE",
        "LC_COLLATE",
        "LC_TIME",
        "LC_MONETARY",
        "LC_NUMERIC",
        "LC_ALL",
        "CHAR_MAX",
    ]

    @property
    @abstractmethod
    def CHAR_MAX(self):
        raise ImportError

    @property
    @abstractmethod
    def Error(self):
        raise ImportError

    @property
    @abstractmethod
    def LC_ALL(self):
        raise ImportError

    @property
    @abstractmethod
    def LC_COLLATE(self):
        raise ImportError

    @property
    @abstractmethod
    def LC_CTYPE(self):
        raise ImportError

    @property
    @abstractmethod
    def LC_MONETARY(self):
        raise ImportError

    @property
    @abstractmethod
    def LC_NUMERIC(self):
        raise ImportError

    @property
    @abstractmethod
    def LC_TIME(self):
        raise ImportError

    def _getdefaultlocale(self):
        return self.myrrh_os.getdefaultlocale()

    def getencoding(self):
        return self.myrrh_os.defaultencoding()

    @abstractmethod
    def setlocale(self, category, value=None):
        ...

    @abstractmethod
    def localeconv(self, category, value=None):
        ...

    # optionals
    # def strcoll(self):
    #    raise AttributeError

    # optional
    # def strxfrm(self):
    #    raise AttributeError
