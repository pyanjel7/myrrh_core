import re
import os


from subprocess import list2cmdline

__all__ = [
    "split",
    "list2cmdline",
    "split",
    "shcmd",
    "winshell_escape_for_cmd_exe",
    "winshell_escape_for_stringyfication_in_cmd",
    "quote",
    "dquote",
]


# function copy from stackoverflow, Mar 9, 2016, author: kxr
# this function is distributed under the terms of CC BY-SA 3.0 licence.
# licence link : https://creativecommons.org/licenses/by-sa/3.0/
# updated to work with bytes argument
# original version : https://stackoverflow.com/questions/33560364/python-windows-parsing-command-lines-with-shlex/35900070#35900070
def _split(s: str, posix, RE_CMD_LEX, qs_replace, word_replace, empty_accu):
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
def split(s: str, posix=(os.name == "posix")):
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


_meta_chars = '()%!^"<>&|'

_meta_re = re.compile("(" + "|".join(re.escape(char) for char in list(_meta_chars)) + ")")
_meta_map = {char: "^%s" % char for char in _meta_chars}
_meta_map_stringify = {char: '"%s"' % char for char in _meta_chars}


# function copy from stackoverflow, Mar 23, 2015, author: Holder Just
# this function is distributed under the terms of CC BY-SA 3.0 licence.
# licence link : https://creativecommons.org/licenses/by-sa/3.0/
# updated to work with bytes argument
# original version : https://stackoverflow.com/questions/29213106/how-to-securely-escape-command-line-arguments-for-the-cmd-exe-shell-on-windows/29215357#29215357
def winshell_escape_for_cmd_exe(arg):
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

    return _meta_re.sub(lambda m: _meta_map[m.group(1)], arg)


# function copy from stackoverflow, Mar 23, 2015, author: Holder Just
# this function is distributed under the terms of CC BY-SA 3.0 licence.
# licence link : https://creativecommons.org/licenses/by-sa/3.0/
# updated to work with bytes argument
# original version : https://stackoverflow.com/questions/29213106/how-to-securely-escape-command-line-arguments-for-the-cmd-exe-shell-on-windows/29215357#29215357
def winshell_escape_for_stringyfication_in_cmd(arg: str):
    return _meta_re.sub(lambda m: _meta_map_stringify[m.group(1)], arg)


_find_unsafe = re.compile(r"[^\w@%\+=:,\./\-<>]", re.ASCII).search


def quote(s: str):
    """Return a shell-escaped version of the string *s*."""
    if not s:
        return "''"
    if _find_unsafe(s) is None:
        return s

    # use single quotes, and put single quotes into double quotes
    # the string $'b is then quoted as '$'"'"'b'
    return "'" + s.replace("'", "'\"'\"'") + "'"


def dquote(s: str):
    """Return a shell-escaped version of the string *s*."""
    if not s:
        return '""'
    if _find_unsafe(s) is None:
        return s

    # use single quotes, and put single quotes into double quotes
    # the string $'b is then quoted as '$'"'"'b'
    return '"' + s + '"'


pattern = re.compile(r"{(\w+)(?::([^}]*}))?}")


def shcmd(template: str, options: dict[str, str]):
    """generate a command line using the template string

    TEMPLATE= anystring|OPTIONAL|TEMPLATE
    OPTIONAL = {KEY[:KEYPATTERN]}
    KEY= str
    KEYPATTERN = anystring|KEY|KEYPATTERN

    examples:
        template="ls {PATH}" with options={'PATH': '/path'} => 'ls /path'
        template="ls {PATH}" with options={'ANOTHER': '/path'} => 'ls '
        template="ls {PATH: -l {PATH}}" with options={'PATH': '/path'} => 'ls -l /path'
        template="ls {PATH: -l {PATH}}" with options={'ANOTHER': '/path'} => 'ls '

    Args:
        template (str): commandline template
        options (dict[bytes, bytes]): a dictionary with optional key value

    Returns:
        bytes: formatted command line
    """
    cmd = template
    for opt in re.finditer(pattern, template):
        optname, optstring = opt.groups()
        optflag = "{%s}" % optname
        optstring = optstring or optflag

        if optname in options:
            optformatted = "%%(%s)s" % optname
            optformatted = optstring.replace(optflag, optformatted)
            cmd = cmd.replace(opt.group(), optformatted)

        else:
            cmd = cmd.replace(opt.group(), "")

    return cmd % options
