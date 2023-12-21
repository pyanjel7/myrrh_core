# -*- coding: utf-8 -*-

"""
**Filemode python module (from python3.x) **

.. note:: this module should not be used outside Myrrh library.

This module implements filemode as specified in python3.x

-----------

"""

import stat

_filemode_table = (
    (
        (stat.S_IFLNK, "l"),
        (stat.S_IFREG, "-"),
        (stat.S_IFBLK, "b"),
        (stat.S_IFDIR, "d"),
        (stat.S_IFCHR, "c"),
        (stat.S_IFIFO, "p"),
    ),
    ((stat.S_IRUSR, "r"),),
    ((stat.S_IWUSR, "w"),),
    ((stat.S_IXUSR | stat.S_ISUID, "s"), (stat.S_ISUID, "S"), (stat.S_IXUSR, "x")),
    ((stat.S_IRGRP, "r"),),
    ((stat.S_IWGRP, "w"),),
    ((stat.S_IXGRP | stat.S_ISGID, "s"), (stat.S_ISGID, "S"), (stat.S_IXGRP, "x")),
    ((stat.S_IROTH, "r"),),
    ((stat.S_IWOTH, "w"),),
    ((stat.S_IXOTH | stat.S_ISVTX, "t"), (stat.S_ISVTX, "S"), (stat.S_IXOTH, "x")),
)


def filemode(mode):
    """
    Convert a file's mode to a string of the form '-rwxrwxrwx'.
    :param mode: stat mode as returned by stat

    :return: given mode formyrrhd string
    :rtype: str
    """
    perm = []
    for table in _filemode_table:
        for bit, char in table:
            if mode & bit == bit:
                perm.append(char)
                break
        else:
            perm.append("-")

    return "".join(perm)
