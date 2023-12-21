import re
import os


from subprocess import list2cmdline as _list2cmdline

__all__ = ["split"]


# function copy from stackoverflow, Mar 9, 2016, author: kxr
# this function is distributed under the terms of CC BY-SA 3.0 licence.
# licence link : https://creativecommons.org/licenses/by-sa/3.0/
# updated to work with bytes argument
# original version : https://stackoverflow.com/questions/33560364/python-windows-parsing-command-lines-with-shlex/35900070#35900070
def _split(s, posix, RE_CMD_LEX, qs_replace, word_replace, empty_accu):
    args = []
    accu = None
    for qs, qss, esc, pipe, word, white, fail in re.findall(RE_CMD_LEX, s):
        if word:
            pass
        elif esc:
            word = esc[1]
        elif white or pipe:
            if accu is not None:
                args.append(accu)
            if pipe:
                args.append(pipe)
            accu = None
            continue
        elif fail:
            word = fail
        elif qs:
            word = qs_replace(qs)
            if posix:
                word = word_replace(word)
        else:
            word = qss  # may be even empty; must be last

        accu = (accu or empty_accu) + word

    if accu is not None:
        args.append(accu)

    return args


# function copy from stackoverflow, Mar 9, 2016, author: kxr
# this function is distributed under the terms of CC BY-SA 3.0 licence.
# licence link : https://creativecommons.org/licenses/by-sa/3.0/
# updated to work with bytes argument
# original version : https://stackoverflow.com/questions/33560364/python-windows-parsing-command-lines-with-shlex/35900070#35900070
def splitb(s, posix=(os.name == "posix")):
    """
    Multi-platform variant of shlex.split for command-line splitting
    For use with subprocess, for argv injection etc. Using fast REGEX
    """
    if posix:
        RE_CMD_LEX = rb""""((?:\\["\\]|[^"])*)"|'([^']*)'|(\\.)|(&&?|\|\|?|\d?>\>?|[<]<?)|([^\s'"\\&|<>]+)|(\s+)|(.)"""
    else:
        RE_CMD_LEX = rb""""((?:""|\\["\\]|[^"])*)"?()|(\\\\(?=\\*")|\\")|(&&?|\|\|?|\d?\>\>?|[<]<?)|([^\s"&|<>]+)|(\s+)|(.)"""

    def qs_replace(qs):
        return qs.replace(b'\\"', b'"').replace(b"\\\\", b"\\")

    def word_replace(word):
        return word.replace(b'""', b'"')

    return _split(s, posix, RE_CMD_LEX, qs_replace, word_replace, empty_accu=b"")


# function copy from stackoverflow, Mar 9, 2016, author: kxr
# this function is distributed under the terms of CC BY-SA 3.0 licence.
# licence link : https://creativecommons.org/licenses/by-sa/3.0/
# simplified version
# original version : https://stackoverflow.com/questions/33560364/python-windows-parsing-command-lines-with-shlex/35900070#35900070
def splits(s, posix=(os.name == "posix")):
    """
    Multi-platform variant of shlex.split for command-line splitting
    For use with subprocess, for argv injection etc. Using fast REGEX
    """
    if posix:
        RE_CMD_LEX = r""""((?:\\["\\]|[^"])*)"|'([^']*)'|(\\.)|(&&?|\|\|?|\d?>\>?|[<]<?)|([^\s'"\\&|<>]+)|(\s+)|(.)"""
    else:
        RE_CMD_LEX = r""""((?:""|\\["\\]|[^"])*)"?()|(\\\\(?=\\*")|\\")|(&&?|\|\|?|\d?\>\>?|[<]<?)|([^\s"&|<>]+)|(\s+)|(.)"""

    def qs_replace(qs):
        return qs.replace('\\"', '"').replace("\\\\", "\\")

    def word_replace(word):
        return word.replace('""', '"')

    return _split(s, posix, RE_CMD_LEX, qs_replace, word_replace, empty_accu="")


def split(s, posix=(os.name == "posix")):
    if isinstance(s, bytes):
        return splitb(s, posix)
    if isinstance(s, str):
        return splits(s, posix)

    raise TypeError('"s" must be of type str or bytes not "%s"' % type(s))


_meta_chars = '()%!^"<>&|'

_meta_re = re.compile("(" + "|".join(re.escape(char) for char in list(_meta_chars)) + ")")
_meta_map = {char: "^%s" % char for char in _meta_chars}

_meta_re_b = re.compile(b"(" + b"|".join(re.escape(char).encode() for char in list(_meta_chars)) + b")")
_meta_map_b = {char.encode(): b"^%s" % char.encode() for char in _meta_chars}
_meta_map_stringify_b = {char.encode(): b'"%s"' % char.encode() for char in _meta_chars}


# function copy from stackoverflow, Mar 23, 2015, author: Holder Just
# this function is distributed under the terms of CC BY-SA 3.0 licence.
# licence link : https://creativecommons.org/licenses/by-sa/3.0/
# updated to work with bytes argument
# original version : https://stackoverflow.com/questions/29213106/how-to-securely-escape-command-line-arguments-for-the-cmd-exe-shell-on-windows/29215357#29215357
def winshell_escape_for_cmd_exe_b(arg):
    # Escape an argument string to be suitable to be passed to cmd.exe on Windows
    #
    # This method takes an argument that is expected to already be properly
    # escaped for receiving program to be properly parsed. This argument
    # will be further escaped to pass the interpolation performed by cmd.exe
    # unchanged
    #
    # Any meta-characters will be escaped, removing the ability to e.g. use redirects or variables
    #
    # @program arg [String] a single command line argument to escape for cmd.exe
    # @return [String] an escaped string suitable to be passed as a program argument to cmd.exe

    return _meta_re_b.sub(lambda m: _meta_map_b[m.group(1)], arg)


# function copy from stackoverflow, Mar 23, 2015, author: Holder Just
# this function is distributed under the terms of CC BY-SA 3.0 licence.
# licence link : https://creativecommons.org/licenses/by-sa/3.0/
# updated to work with bytes argument
# original version : https://stackoverflow.com/questions/29213106/how-to-securely-escape-command-line-arguments-for-the-cmd-exe-shell-on-windows/29215357#29215357
def winshell_escape_for_stringyfication_in_cmdb(arg):
    return _meta_re_b.sub(lambda m: _meta_map_stringify_b[m.group(1)], arg)


def list2cmdlineb(seq, encode=os.fsencode, decode=os.fsdecode):
    if not len(seq):
        return b""

    if isinstance(seq[0], bytes):
        return encode(_list2cmdline(map(decode, seq)))

    return _list2cmdline(seq)


_find_unsafe = re.compile(rb"[^\w@%\+=:,\./\-<>]", re.ASCII).search


def quote(s):
    """Return a shell-escaped version of the string *s*."""
    if not s:
        return b"''"
    if _find_unsafe(s) is None:
        return s

    # use single quotes, and put single quotes into double quotes
    # the string $'b is then quoted as '$'"'"'b'
    return b"'" + s.replace(b"'", b"'\"'\"'") + b"'"


def dquote(s):
    """Return a shell-escaped version of the string *s*."""
    if not s:
        return b'""'
    if _find_unsafe(s) is None:
        return s

    # use single quotes, and put single quotes into double quotes
    # the string $'b is then quoted as '$'"'"'b'
    return b'"' + s + b'"'
