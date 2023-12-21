from myrrh.framework.msh.madvsh import AbcAdvSh

_cmd_internal = (
    b"true",
    b".",
    b"alias",
    b"bg",
    b"command",
    b"cd",
    b"echo",
    b"eval",
    b"exec",
    b"exit",
    b"export",
    b"fc",
    b"fg",
    b"getopts",
    b"hash",
    b"pwd",
    b"read",
    b"readonly",
    b"printf",
    b"set",
    b"shift",
    b"test",
    b"times",
    b"trap",
    b"type",
    b"ulimit",
    b"umask",
    b"unalias",
    b"unset",
    b"$",
    b"!",
    b"elif",
    b"fi",
    b"while",
    b"case",
    b"else",
    b"for",
    b"then",
    b"{",
    b"}",
    b"do",
    b"done",
    b"until",
    b"if",
    b"esac",
)

_cmd_operators = set((b"&&", b"|", b"||", b";", b";;", b"&", b">>", b"<<", b"<", b">", b">|", b">&", b"<&", b"<<-", b"<>", b"(", b")"))


__mlib__ = "AdvSh"


class AdvSh(AbcAdvSh):
    def initialize_stat(self):
        self.execute(b"%(echo)s init" % self.myrrh_os.getbinb, count=1).values()

    def _calibration_execution(self, count):
        return self.execute(b"%(sleep)s 1" % self.myrrh_os.getbinb, count=count)
