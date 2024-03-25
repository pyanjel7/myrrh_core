from myrrh.framework.msh.madvsh import AbcAdvSh

_cmd_internal = (
    "true",
    ".",
    "alias",
    "bg",
    "command",
    "cd",
    "echo",
    "eval",
    "exec",
    "exit",
    "export",
    "fc",
    "fg",
    "getopts",
    "hash",
    "pwd",
    "read",
    "readonly",
    "printf",
    "set",
    "shift",
    "test",
    "times",
    "trap",
    "type",
    "ulimit",
    "umask",
    "unalias",
    "unset",
    "$",
    "!",
    "elif",
    "fi",
    "while",
    "case",
    "else",
    "for",
    "then",
    "{",
    "}",
    "do",
    "done",
    "until",
    "if",
    "esac",
)

_cmd_operators = set(("&&", "|", "||", ";", ";;", "&", ">>", "<<", "<", ">", ">|", ">&", "<&", "<<-", "<>", "(", ")"))


__mlib__ = "AdvSh"


class AdvSh(AbcAdvSh):
    def initialize_stat(self):
        self.execute("%(echo)s init" % self.myrrh_os.getbin, count=1).values()

    def _calibration_execution(self, count):
        return self.execute("%(sleep)s 1" % self.myrrh_os.getbin, count=count)
