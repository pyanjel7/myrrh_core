import threading

from myrrh.utils import mshlex

from myrrh.utils import mstring
from myrrh.core.services.system import ExecutionFailureCauseRVal

from myrrh.core.services.system import AbcRuntime
from myrrh.framework.mpython import mimportlib


from myrrh.resources.textfsm import getparser

__mlib__ = "WinReg"


def _convert_reg_sz(v):
    v = str(v)
    return v[: v.index("\0")] if "\0" in v else v


def _convert_reg_multi_sz(v):
    return "\\0".join(filter(None, v))


def _revert_reg_multi_sz(v):
    return v.split("\\0") if v else []


class WinReg(AbcRuntime):
    """
    Notice : - RE_MULTI_SZ does not support empty string
             - Big data unsupported
    """

    __frameworkpath__ = "mpython.winreg"

    tempfile = mimportlib.module_property("tempfile")
    os = mimportlib.module_property("os")

    QUERY_PARSER = staticmethod(getparser("nt_reg"))

    def __init__(self, system=None):
        self._hkeys = dict()

        self.HKEY_CLASSES_ROOT = self.PyHKEY(0, self, None, "HKEY_CLASSES_ROOT")
        self.HKEY_CURRENT_USER = self.PyHKEY(0, self, None, "HKEY_CURRENT_USER")
        self.HKEY_LOCAL_MACHINE = self.PyHKEY(0, self, None, "HKEY_LOCAL_MACHINE")
        self.HKEY_USERS = self.PyHKEY(0, self, None, "HKEY_USERS")
        self.HKEY_PERFORMANCE_DATA = self.PyHKEY(0, self, None, "HKEY_PERFORMANCE_DATA")
        self.HKEY_CURRENT_CONFIG = self.PyHKEY(0, self, None, "HKEY_CURRENT_CONFIG")
        self.HKEY_DYN_DATA = self.PyHKEY(0, self, None, "HKEY_DYN_DATA")

        self._default_key = None

    @property
    def default_key(self):
        if self._default_key is None:
            self._default_key, _, _ = self.HKEY_CURRENT_USER._query_default()

    class PyHKEY:
        def __init__(self, handle, winreg, hkey, key="", *, computer=None):
            self.handle = handle
            self.winreg = winreg
            self.myrrh_os = winreg.myrrh_os

            self._closed = False
            self._detached = False

            self._lock = threading.Lock()
            self.__subkeys = None
            self.__values = None

            self._computer = computer or (hkey and hkey._computer) or "."

            if hkey:
                self.key = self._join(hkey.key, key) if key else hkey.key
            else:
                self.key = key

        @property
        def _values(self):
            if self.__values is None:
                self._query()

            return self.__values

        @property
        def _subkeys(self):
            if self.__subkeys is None:
                self._query()

            return self.__subkeys

        def __del__(self):
            if not self._detached:
                self.Detach()

        def __int__(self):
            return self.handle

        def __bool__(self):
            return not self._closed

        def __enter__(self):
            return self

        def __exit__(self, *exec_info):
            if not self._detached:
                self.Close()

        def _join(self, *a):
            return "\\".join(a)

        @property
        def path(self):
            return self._join("\\", self._computer, self.key)

        def Detach(self):
            if self.handle and not self._detached:
                self.winreg._pop(self.handle)

            self._detached = True
            return self.handle

        def Close(self):
            self.Detach()
            self._closed = True
            self.handle = 0

        def _new(self, handle, sub_key=None):
            if not (sub_key):
                return self
            return WinReg.PyHKEY(handle, self.winreg, self, sub_key, computer=self._computer)

        def cmd(self, *a, **kwa):
            return self.myrrh_os.cmd(*a, **kwa)

        def sh_escape_bytes(self, bytes_or_str):
            value = self.myrrh_os.fsencode(bytes_or_str)
            return mshlex.winshell_escape_for_stringyfication_in_cmdb(value)

        def _find_value_index(self, name):
            for a in self._values:
                n, _, _ = a
                if n == name:
                    return self._values.index(a)

        def _add_value(self, value):
            idx = self._find_value_index(value[0])
            if idx is None:
                self._values.append(value)
            else:
                self._values[idx] = value

        def _query_default(self):
            key_path = self.myrrh_os.p(self.path)

            o, e, r = self.myrrh_os.cmd(
                b'%(reg_utf8)s QUERY "%(path)s" /ve',
                path=self.myrrh_os.sh_escape_bytes(key_path),
            )
            ExecutionFailureCauseRVal(self, e, r, 0, key_path).check()

            with self.winreg.QUERY_PARSER as textfsm:
                fsm = textfsm.ParseText(o)

            return fsm[0][1:] if len(fsm[0]) else tuple()

        def _query(self, o=None):
            key_path = self.myrrh_os.p(self.path)

            if o is None:
                o, e, r = self.myrrh_os.cmd(
                    b'%(reg_utf8)s QUERY "%(path)s"',
                    path=self.myrrh_os.sh_escape_bytes(key_path),
                )
                try:
                    ExecutionFailureCauseRVal(self, e, r, 0, key_path).check()
                except ExecutionFailureCauseRVal:
                    raise FileNotFoundError(key_path)

            with self._lock:
                with self.winreg.QUERY_PARSER as textfsm:
                    fsm = textfsm.ParseText(o)

                self.__subkeys = list()
                self.__values = list()
                for line in fsm:
                    k, n, v, t = line

                    if k != self.key:
                        k = self.winreg.os.path.basename(k)

                        try:
                            self._subkeys.index(k)
                        except ValueError:
                            self._subkeys.append(k)

                    else:
                        if not t:
                            continue

                        if n == self.winreg.default_key:
                            n = ""

                        stype, value_conv = self.winreg._TYPE_CONVERT[t]
                        value = value_conv(v)

                        self._add_value((n, value, stype))

        def _create(self):
            o, e, r = self.myrrh_os.cmd(
                b'( %(reg_utf8)s QUERY "%(path)s" 2>NUL ) || ( ( %(reg_utf8)s ADD "%(path)s" 1>NUL ) && ( %(reg_utf8)s DELETE "%(path)s" /ve /f 1>NUL ) && %(reg_utf8)s QUERY "%(path)s")',
                path=self.myrrh_os.sh_escape_bytes(self.key_path),
            )
            ExecutionFailureCauseRVal(self, e, r, 0, self.path).check()
            self._query(o)

        def _delete(self):
            key_path = self.myrrh_os.p(self.path)

            _, e, r = self.myrrh_os.cmd(
                b'%(reg_utf8)s DELETE "%(path)s" /f',
                path=self.myrrh_os.sh_escape_bytes(key_path),
            )
            ExecutionFailureCauseRVal(self, e, r, 0, self.path).check()

        def _delete_value(self, value):
            key_path = self.myrrh_os.p(self.path)
            value = self.myrrh_os.shdecode(value)

            o, e, r = self.myrrh_os.cmd(
                b'%(reg_utf8)s DELETE  "%(path)s" /v "%(value)s" /f && %(reg_utf8)s QUERY "%(path)s"',
                path=self.myrrh_os.sh_escape_bytes(key_path),
                value=self.myrrh_os.sh_escape_bytes(value),
            )
            ExecutionFailureCauseRVal(self, e, r, 0, self.path).check()
            self._query(o)

        def _loadkey(self, filename):
            key_path = self.myrrh_os.p(self.path)
            filename = self.myrrh_os.p(filename)

            o, e, r = self.myrrh_os.cmd(
                b'%(reg_utf8)s LOAD "%(path)s" "%(filename)s" && %(reg_utf8)s QUERY "%(path)s"',
                path=self.myrrh_os.sh_escape_bytes(key_path),
                value=self.myrrh_os.sh_escape_bytes(filename),
            )
            ExecutionFailureCauseRVal(self, e, r, 0, self.path).check()
            self._query(o)

        def _save(self, filename):
            key_path = self.myrrh_os.p(self.path)
            filename = self.myrrh_os.p(filename)

            _, e, r = self.myrrh_os.cmd(
                b'%(reg_utf8)s SAVE "%(path)s" "%(filename)s"',
                path=self.myrrh_os.sh_escape_bytes(key_path),
                value=self.myrrh_os.sh_escape_bytes(filename),
            )
            ExecutionFailureCauseRVal(self, e, r, 0, self.path).check()

        def _set_value(self, type, value, value_name=""):
            key_path = self.myrrh_os.p(self.path)

            stype, value_conv = self.winreg._TYPE_CONVERT[type]
            svalue = value_conv(value) if value is not None else ""

            stype = self.myrrh_os.shdecode(value)
            svalue = self.myrrh_os.shdecode(value)

            o, e, r = self.myrrh_os.cmd(
                b'%(reg_utf8)s ADD "%(path)s"  %(value_name)s /t %(type)s /d "%(value)s" /f && %(reg_utf8)s QUERY "%(path)s" ',
                path=self.myrrh_os.sh_escape_bytes(key_path),
                value=self.myrrh_os.sh_escape_bytes(svalue),
                type=self.myrrh_os.sh_escape_bytes(stype),
                value_name=(b'/v "%s"' % self.myrrh_os.sh_escape_bytes(value_name)) if value_name else b"",
            )

            ExecutionFailureCauseRVal(self, e, r, 0, self.path).check()

            self._query(o)

    HKEYType = PyHKEY

    HKEY_CLASSES_ROOT: PyHKEY | None = None
    HKEY_CURRENT_USER: PyHKEY | None = None
    HKEY_LOCAL_MACHINE: PyHKEY | None = None
    HKEY_USERS: PyHKEY | None = None
    HKEY_PERFORMANCE_DATA: PyHKEY | None = None
    HKEY_CURRENT_CONFIG: PyHKEY | None = None
    HKEY_DYN_DATA: PyHKEY | None = None

    REG_NONE = 0
    REG_SZ = 1
    REG_EXPAND_SZ = 2
    REG_BINARY = 3
    REG_DWORD = 4
    REG_DWORD_LITTLE_ENDIAN = 4
    REG_DWORD_BIG_ENDIAN = 5
    REG_LINK = 6
    REG_MULTI_SZ = 7
    REG_RESOURCE_LIST = 8
    REG_FULL_RESOURCE_DESCRIPTOR = 9
    REG_RESOURCE_REQUIREMENTS_LIST = 10
    REG_QWORD_LITTLE_ENDIAN = 11
    REG_QWORD = 11

    _TYPE_CONVERT = {
        "REG_NONE": (REG_NONE, str),
        "REG_SZ": (REG_SZ, str),
        "REG_EXPAND_SZ": (REG_EXPAND_SZ, str),
        "REG_BINARY": (REG_BINARY, lambda v: bytes.fromhex(v) if v != "" else None),
        "REG_DWORD": (REG_DWORD, mstring.str2int),
        "REG_MULTI_SZ": (REG_MULTI_SZ, _revert_reg_multi_sz),
        "REG_QWORD": (REG_QWORD, mstring.str2int),
        REG_NONE: ("REG_NONE", str),
        REG_SZ: ("REG_SZ", _convert_reg_sz),
        REG_EXPAND_SZ: ("REG_EXPAND_SZ", str),
        REG_BINARY: ("REG_BINARY", lambda v: v.hex() if v is not None else ""),
        REG_DWORD: ("REG_DWORD", str),
        REG_DWORD_BIG_ENDIAN: ("REG_DWORD", str),
        REG_LINK: ("REG_SZ", str),
        REG_MULTI_SZ: ("REG_MULTI_SZ", _convert_reg_multi_sz),
        REG_RESOURCE_LIST: ("REG_MULTI_SZ", str),
        REG_FULL_RESOURCE_DESCRIPTOR: ("REG_SZ", str),
        REG_RESOURCE_REQUIREMENTS_LIST: ("REG_MULTI_SZ", str),
        REG_QWORD: ("REG_QWORD", str),
    }

    KEY_ALL_ACCESS = 0xF003F
    KEY_QUERY_VALUE = 0x1
    KEY_SET_VALUE = 0x2
    KEY_CREATE_SUB_KEY = 0x4
    KEY_ENUMERATE_SUB_KEYS = 0x8
    KEY_NOTIFY = 0x10
    KEY_CREATE = 0x20
    KEY_WRITE = 0x20006
    KEY_READ = 0x20019
    KEY_EXECUTE = 0x20019
    KEY_CREATE_LINK = 0x20

    KEY_WOW64_64KEY = 0x0100
    KEY_WOW64_32KEY = 0x0200

    DEFAULT_NEW_KEY = "new key"

    REG_CREATED_NEW_KEY = 1
    REG_REFRESH_HIVE = 2

    REG_WHOLE_HIVE_VOLATILE = 1

    REG_LEGAL_CHANGE_FILTER = 0x1000000F
    REG_LEGAL_OPTION = 0x1F

    REG_NOTIFY_CHANGE_NAME = 1
    REG_NOTIFY_CHANGE_ATTRIBUTES = 2
    REG_NOTIFY_CHANGE_LAST_SET = 4
    REG_NOTIFY_CHANGE_SECURITY = 8

    REG_OPENED_EXISTING_KEY = 2

    REG_OPTION_RESERVED = 0
    REG_OPTION_NON_VOLATILE = 0
    REG_OPTION_VOLATILE = 1
    REG_OPTION_CREATE_LINK = 2
    REG_OPTION_BACKUP_RESTORE = 4
    REG_OPTION_OPEN_LINK = 8

    REG_NO_LAZY_FLUSH = 4

    _START_HANDLE = 777

    def _to_PyHKEY(self, handle):
        if isinstance(handle, int):
            try:
                return self._hkeys[handle]
            except KeyError:
                pass

            raise OSError(6, "Invalid descriptor")

        if isinstance(handle, WinReg.PyHKEY):
            return handle

        raise TypeError("The object is not a PyHKEY object")

    def _to_RefHKEY(self, handle):
        if isinstance(handle, int):
            try:
                return self._hkeys[handle].handle
            except KeyError:
                pass

            raise OSError(6, "Invalid descriptor")

        if isinstance(handle, WinReg.PyHKEY):
            return handle.handle

        raise TypeError("The object is not a PyHKEY object")

    def _new_HANDLE(self, handle=None):
        if not handle:
            handle = self._START_HANDLE
            self._START_HANDLE += 1
        return handle

    def _close(self, handle):
        hkey = self._to_PyHKEY(handle)
        hkey.Close()

    def _pop(self, hkey):
        handle = self._to_RefHKEY(hkey)
        return self._hkeys.pop(handle)

    def _add(self, hkey):
        self._hkeys[hkey.handle] = hkey
        return hkey

    def CloseKey(self, hkey):
        hkey = self._to_PyHKEY(hkey)
        hkey.Close()

    def ConnectRegistry(self, computer_name, key):
        hkey = self._to_PyHKEY(key)
        hkey = self.PyHKEY(self._new_HANDLE(), self, hkey, computer=computer_name)

        hkey._query()

        return self._add(hkey)

    def CreateKey(self, key, sub_key):
        hkey = self._to_PyHKEY(key)
        hkey = hkey._new(self._new_HANDLE(), sub_key)

        hkey._create()

        return self._add(hkey)

    def CreateKeyEx(self, key, sub_key, reserved=0, access=KEY_WRITE):
        # Access is not used in Myrrh
        return self.CreateKey(key, sub_key)

    def DeleteKey(self, key, sub_key):
        hkey = self._to_PyHKEY(key)
        hkey = hkey._new(0, sub_key)
        hkey._delete()

    def DeleteKeyEx(self, key, sub_key, access=KEY_WOW64_64KEY, reserved=0):
        # Access is not used in Myrrh
        return self.DeleteKey(key, sub_key)

    def DeleteValue(self, key, value):
        hkey = self._to_PyHKEY(key)
        hkey._delete_value(value)

    def EnumKey(self, key, index):
        hkey = self._to_PyHKEY(key)
        try:
            return hkey._subkeys[index]
        except IndexError:
            pass

        raise OSError(259, "No data found")

    def EnumValue(self, key, index):
        hkey = self._to_PyHKEY(key)

        try:
            return hkey._values[index]
        except IndexError:
            pass

        raise OSError(259, "No data found")

    def ExpandEnvironmentStrings(self, str):
        out, err, rval = self.myrrh_os.cmd(b"%(echo)s %(str)s", str=self.myrrh_os.shencode(str))
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        return out.strip()

    def FlushKey(self, key):
        hkey = self._to_PyHKEY(key)
        hkey._query()

    def LoadKey(self, key, sub_key, file_name):
        hkey = self._to_PyHKEY(key)
        hkey = hkey._new(0, sub_key)
        hkey._loadkey(file_name)

    def OpenKey(self, key, sub_key, reserved=0, access=KEY_READ):
        hkey = self._to_PyHKEY(key)
        hkey = hkey._new(0, sub_key)
        hkey._query()
        hkey.handle = self._new_HANDLE()
        self._add(hkey)
        return hkey

    def OpenKeyEx(self, key, sub_key, reserved=0, access=KEY_READ):
        return self.OpenKey(key, sub_key, reserved, access)

    def QueryInfoKey(self, key):
        hkey = self._to_PyHKEY(key)
        hkey._query()
        return (len(hkey._subkeys), len(hkey._values), 0)

    def QueryValue(self, key, sub_key):
        hkey = self._to_PyHKEY(key)
        nkey = hkey._new(0, sub_key)
        if nkey is not hkey:
            nkey._query()
            hkey = nkey
        idx = hkey._find_value_index("")
        if idx is None:
            raise FileNotFoundError(key)

        return hkey._values[idx][1]

    def QueryValueEx(self, key, value_name):
        hkey = self._to_PyHKEY(key)
        idx = hkey._find_value_index(value_name)
        if idx is None:
            raise FileNotFoundError(key)
        return hkey._values[idx][1:]

    def SaveKey(self, key, file_name):
        hkey = self._to_PyHKEY(key)
        hkey._save(file_name)

    def SetValue(self, key, sub_key, type, value):
        hkey = self._to_PyHKEY(key)

        if not sub_key:
            sub_key = self.DEFAULT_NEW_KEY
            inc = 1
            while sub_key in hkey._subkeys:
                sub_key = self.DEFAULT_NEW_KEY + " #%d" % inc
                inc += 1

        nkey = hkey._new(0, sub_key)
        nkey._set_value(type, value)

    def SetValueEx(self, key, value_name, reserved, type, value):
        hkey = self._to_PyHKEY(key)
        hkey._set_value(type, value, value_name)

    def DisableReflectionKey(self, key):
        raise NotImplementedError

    def EnableReflectionKey(self, key):
        raise NotImplementedError

    def QueryReflectionKey(self, key):
        raise NotImplementedError
