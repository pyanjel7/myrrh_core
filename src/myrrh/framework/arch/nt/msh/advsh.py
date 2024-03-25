from myrrh.framework.msh.madvsh import AbcAdvSh

_cmd_internal = (
    "assoc",
    "call",
    "cd",
    "cls",
    "color",
    "copy",
    "date",
    "del",
    "dir",
    "echo",
    "endlocal",
    "erase",
    "exit",
    "for",
    "ftype",
    "goto",
    "if",
    "md",
    "mklink",
    "move",
    "path",
    "pause",
    "popd",
    "prompt",
    "pushd",
    "rem",
    "ren",
    "rd",
    "set",
    "setlocal",
    "shift",
    "start",
    "time",
    "title",
    "type",
    "ver",
    "verify",
    "vol",
    "::",
    "(",
    "@",
)
_cmd_operators = set(("&&", "|", "||", ";", ";;", "&", ">>", "<<", "<", ">", ">|", ">&", "<&", "<<-", "<>", "(", ")"))


__mlib__ = "AdvSh"


class AdvSh(AbcAdvSh):
    def initialize_stat(self):
        self.execute("%(ping)s -n 1 127.0.0.1" % self.myrrh_os.getbin, count=1).values()

    def _calibration_execution(self, count):
        return self.execute("%(ping)s -n 2 127.0.0.1" % self.myrrh_os.getbin, count=count)
