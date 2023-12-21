from myrrh.core.services.system import AbcRuntime

__mlib__ = "AbcMsvcrt"


class AbcMsvcrt(AbcRuntime):
    __frameworkpath__ = "mpython.mmsvcrt"

    def open_osfhandle(self, __handle: int, __flags: int) -> int:
        return __handle

    def get_osfhandle(self, __handle: int) -> int:
        return self.myrrh_syscall.gethandle(__handle).detach()
