from myrrh.framework.msh.madvsh import AbcAdvSh

_cmd_internal = (
    b"assoc",
    b"call",
    b"cd",
    b"cls",
    b"color",
    b"copy",
    b"date",
    b"del",
    b"dir",
    b"echo",
    b"endlocal",
    b"erase",
    b"exit",
    b"for",
    b"ftype",
    b"goto",
    b"if",
    b"md",
    b"mklink",
    b"move",
    b"path",
    b"pause",
    b"popd",
    b"prompt",
    b"pushd",
    b"rem",
    b"ren",
    b"rd",
    b"set",
    b"setlocal",
    b"shift",
    b"start",
    b"time",
    b"title",
    b"type",
    b"ver",
    b"verify",
    b"vol",
    b"::",
    b"(",
    b"@",
)
_cmd_operators = set((b"&&", b"|", b"||", b";", b";;", b"&", b">>", b"<<", b"<", b">", b">|", b">&", b"<&", b"<<-", b"<>", b"(", b")"))


__mlib__ = "AdvSh"


class AdvSh(AbcAdvSh):
    def initialize_stat(self):
        self.execute(b"%(ping)s -n 1 127.0.0.1" % self.myrrh_os.getbinb, count=1).values()

    def _calibration_execution(self, count):
        return self.execute(b"%(ping)s -n 2 127.0.0.1" % self.myrrh_os.getbinb, count=count)
