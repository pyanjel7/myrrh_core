import typing

from myrrh.core.interfaces import abstractmethod, ABC
from myrrh.core.services.system import AbcRuntimeDelegate

from . import mbuiltins
from . import mimportlib

__mlib__ = "AbcPlatform"


class _interface(ABC):
    import platform as local_platform

    @property
    @abstractmethod
    def uname_result(self) -> local_platform.uname_result:
        ...

    @property
    @abstractmethod
    def _ver_output(self):
        ...

    @property
    @abstractmethod
    def _WIN32_CLIENT_RELEASES(self):
        ...

    @property
    @abstractmethod
    def _WIN32_SERVER_RELEASES(self):
        ...

    @property
    @abstractmethod
    def _Processor(self):
        ...

    @property
    @abstractmethod
    def _sys_version(self):
        ...

    @property
    @abstractmethod
    def _sys_version_cache(self):
        ...

    @property
    @abstractmethod
    def _os_release_candidates(self):
        ...

    @abstractmethod
    def win32_is_iot(self) -> bool:
        ...

    @abstractmethod
    def win32_edition(self) -> str:
        ...

    @abstractmethod
    def win32_ver(self, release: str = ..., version: str = ..., csd: str = ..., ptype: str = ...) -> tuple[str, str, str, str]:
        ...

    @abstractmethod
    def mac_ver(self, release: str = ..., version: str = ..., csd: str = ..., ptype: str = ...) -> tuple[str, str, str, str]:
        ...

    @abstractmethod
    def java_ver(
        self,
        release: str = ...,
        vendor: str = ...,
        vminfo: tuple[str, str, str] = ...,
        osinfo: tuple[str, str, str] = ...,
    ) -> tuple[str, str, tuple[str, str, str], tuple[str, str, str]]:
        ...

    @abstractmethod
    def architecture(self, executable: str = ..., bits: str = ..., linkage: str = ...) -> tuple[str, str]:
        ...

    @abstractmethod
    def uname(self) -> str:
        ...

    @abstractmethod
    def system(self) -> str:
        ...

    @abstractmethod
    def node(self) -> str:
        ...

    @abstractmethod
    def release(self) -> str:
        ...

    @abstractmethod
    def version(self) -> str:
        ...

    @abstractmethod
    def machine(self) -> str:
        ...

    @abstractmethod
    def processor(self) -> str:
        ...

    @abstractmethod
    def python_implementation(self) -> str:
        ...

    @abstractmethod
    def python_version(self) -> str:
        ...

    @abstractmethod
    def python_version_tuple(self) -> tuple[str, str, str]:
        ...

    @abstractmethod
    def python_branch(self) -> str:
        ...

    @abstractmethod
    def python_revision(self) -> str:
        ...

    @abstractmethod
    def python_build(self) -> tuple[str, str]:
        ...

    @abstractmethod
    def python_compiler(self) -> str:
        ...

    @abstractmethod
    def platform(self, aliased: bool = ..., terse: bool = ...) -> str:
        ...

    @abstractmethod
    def freedesktop_os_release(self) -> dict[str, str]:
        ...

    @abstractmethod
    def system_alias(
        self, system: typing.Any, release: typing.Any, version: typing.Any
    ) -> tuple | tuple[typing.Any | typing.Literal["Solaris", "Windows"], str | typing.Any, typing.Any,]:
        ...

    @abstractmethod
    def libc_ver(
        self,
        executable: typing.Any | None = None,
        lib: str = "",
        version: str = "",
        chunksize: int = 16384,
    ) -> typing.Any:
        ...

    @abstractmethod
    def _parse_os_release(self):
        ...

    @abstractmethod
    def _platform_cache(self):
        ...

    @abstractmethod
    def _follow_symlinks(self):
        ...

    @abstractmethod
    def _syscmd_ver(self):
        ...

    @abstractmethod
    def _norm_version(self):
        ...

    @abstractmethod
    def _uname_cache(self):
        ...

    @abstractmethod
    def _node(self):
        ...

    @abstractmethod
    def _syscmd_file(self):
        ...


class AbcPlatform(_interface, AbcRuntimeDelegate):
    __frameworkpath__ = "mpython.mplatform"

    __doc__ = _interface.local_platform.__doc__

    os = mimportlib.module_property("os")
    sys = mimportlib.module_property("sys")

    __delegated__ = {_interface: _interface.local_platform}
    __delegate_check_type__ = False

    def __init__(self, *a, **kwa):
        mod = mbuiltins.wrap_module(self.local_platform, self)

        mod._syscmd_ver = self._myrrh_syscmd_ver
        mod.java_ver = self._myrrh_java_ver
        mod._node = self._myrrh_node
        mod._syscmd_file = self._myrrh_syscmd_file
        mod._Processor.from_subprocess = self._myrrh_from_subprocess

        self.__delegate__(_interface, mod)

    def _myrrh_syscmd_ver(
        self,
        system="",
        release="",
        version="",
        supported_platforms=("win32", "win16", "dos"),
    ):
        """Tries to figure out the OS version used and returns
        a tuple (system, release, version).

        It uses the "ver" shell command for this which is known
        to exists on Windows, DOS. XXX Others too ?

        In case this fails, the given parameters are used as
        defaults.

        """
        sys = self.sys
        _ver_output = self._ver_output
        _norm_version = self._norm_version

        if sys.platform not in supported_platforms:
            return system, release, version

        # Try some common cmd strings
        for cmd in (b"ver", b"command /c ver", b'cmd /c "ver"'):
            # try:
            #    info = subprocess.check_output(cmd,
            #                                stdin=subprocess.DEVNULL,
            #                                stderr=subprocess.DEVNULL,
            #                                text=True,
            #                                encoding="locale",
            #                                shell=True)
            # except (OSError, subprocess.CalledProcessError) as why:
            #    #print('Command %s failed: %s' % (cmd, why))
            #    continue
            # else:
            #    break
            info, e, r = self.myrrh_os.cmd(cmd)
            if not r:
                break
        else:
            return system, release, version

        # Parse the output
        info = info.strip()
        m = _ver_output.match(info)
        if m is not None:
            system, release, version = m.groups()
            # Strip trailing dots from version and release
            if release[-1] == ".":
                release = release[:-1]
            if version[-1] == ".":
                version = version[:-1]
            # Normalize the version and build strings (eliminating additional
            # zeros)
            version = _norm_version(version)
        return system, release, version

    def _myrrh_java_ver(self, release="", vendor="", vminfo=("", "", ""), osinfo=("", "", "")):
        """Version interface for Jython.

        Returns a tuple (release, vendor, vminfo, osinfo) with vminfo being
        a tuple (vm_name, vm_release, vm_vendor) and osinfo being a
        tuple (os_name, os_version, os_arch).

        Values which cannot be determined are set to the defaults
        given as parameters (which all default to '').

        """
        import re

        _, e, _ = self.myrrh_os.cmd(b"%(java)s -XshowSettings:properties", java=b"java")

        props = re.findall(r"([.\w]+) = ([\S ]+)", e)
        if not props:
            return release, vendor, vminfo, osinfo

        props = dict(props)

        vendor = props.get("java.vendor", vendor)
        release = props.get("java.version", release)

        vm_name, vm_release, vm_vendor = vminfo
        vm_name = props.get("java.vm.name", vm_name)
        vm_vendor = props.get("java.vm.vendor", vm_vendor)
        vm_release = props.get("java.vm.version", vm_release)
        vminfo = vm_name, vm_release, vm_vendor

        os_name, os_version, os_arch = osinfo
        os_arch = props.get("java.os.arch", os_arch)
        os_name = props.get("java.os.name", os_name)
        os_version = props.get("java.os.version", os_version)
        osinfo = os_name, os_version, os_arch

        return release, vendor, vminfo, osinfo

    def _myrrh_node(self, default=""):
        o, _, r = self.myrrh_os.cmd(b"%(hostname)s", hostname=b"hostname")
        if r:
            return default
        return o.strip()

    def _myrrh_syscmd_file(self, target, default=""):
        """Interface to the system's file command.

        The function uses the -b option of the file command to have it
        omit the filename in its output. Follow the symlinks. It returns
        default in case the command should fail.

        """
        sys = self.sys
        _follow_symlinks = self._follow_symlinks
        os = self.os

        if sys.platform in ("dos", "win32", "win16"):
            # XXX Others too ?
            return default

        # try:
        #    subprocess = self.subprocess
        # except (ImportError):
        #    return default
        target = _follow_symlinks(target)
        # "file" output is locale dependent: force the usage of the C locale
        # to get deterministic behavior.
        env = dict(os.environ, LC_ALL="C")
        # try:
        #    # -b: do not prepend filenames to output lines (brief mode)
        #    output = subprocess.check_output(['file', '-b', target],
        #                                    stderr=subprocess.DEVNULL,
        #                                    env=env)
        # except (OSError, subprocess.CalledProcessError):
        #    return default
        output, _, rval = self.myrrh_os.cmd(
            b"%(file)s -b %(target)s",
            file=b"file",
            target=self.myrrh_os.fsencode(target),
            execute_env=env,
        )
        if not output or rval:
            return default
        # With the C locale, the output should be mostly ASCII-compatible.
        # Decode from Latin-1 to prevent Unicode decode error.
        return output.decode("latin-1")

    def _myrrh_from_subprocess(self):
        """
        Fall back to `uname -p`
        """
        o, _, r = self.myrrh_os.cmd(b"%(uname)s", uname=b"uname")
        if r:
            return None
        return o.strip()
