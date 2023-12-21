from myrrh.framework.mpython.msys import _interface as Sys
from myrrh.framework.mpython.mgzip import _interface as Gzip
from myrrh.framework.mpython.mfnmatch import _interface as Fnmatch
from myrrh.framework.mpython.mshutil import _interface as Shutil
from myrrh.framework.mpython.mglob import _interface as Glob
from myrrh.framework.mpython.mio import _interface as Io
from myrrh.framework.mpython.msubprocess import _interface as Subprocess
from myrrh.framework.mpython.mplatform import _interface as Platform
from myrrh.framework.mpython.msysconfig import AbcSysConfig
from myrrh.framework.mpython.mtarfile import _interface as Tarfile
from myrrh.framework.mpython.mtempfile import _interface as Tempfile
from myrrh.framework.mpython.mlocale import _interface as Locale

from myrrh.framework.mpython._mosenv import AbcOsEnv
from myrrh.framework.mpython._mosfs import AbcOsFs
from myrrh.framework.mpython._mosfile import AbcOsFile
from myrrh.framework.mpython._mosprocess import AbcOsProcess
from myrrh.framework.mpython.mos import AbcOs


class Os(AbcOsEnv, AbcOsFs, AbcOsFile, AbcOsProcess, AbcOs):
    ...


os: Os
sys: Sys
gzip: Gzip
fnmatch: Fnmatch
shutil: Shutil
glob: Glob
io: Io
subprocess: Subprocess
platform: Platform
sysconfig: AbcSysConfig
tarfile: Tarfile
tempfile: Tempfile
locale: Locale

try:
    from myrrh.framework.arch.posix.mpython.mpwd import AbcPwd

    pwd: AbcPwd
except ImportError:
    ...

try:
    from myrrh.framework.arch.posix.mpython.mgrp import AbcGrp

    grp: AbcGrp
except ImportError:
    ...
