import gettext
import os

from errno import *  # noqa: F403
import warnings

default_errorno = 15

posix_error_mappings = {
    "No such file or directory": ENOENT,  # noqa : F405
    "not found": ENOENT,  # noqa : F405
    "Permission denied": EACCES,  # noqa : F405
    "Too many levels of symbolic links": ELOOP,  # noqa : F405
    "Not enough space": ENOMEM,  # noqa : F405
    "Not a directory": ENOTDIR,  # noqa : F405
    "Operation not permitted": EPERM,  # noqa : F405
    "No such process": ESRCH,  # noqa : F405
    "Try again": EAGAIN,  # noqa : F405
    "Too many open files": EMFILE,  # noqa : F405
    "File too large": EFBIG,  # noqa : F405
    "Broken pipe": EPIPE,  # noqa : F405
    "Directory nonexistent": ENOENT,  # noqa : F405
    "Unknown error": 15,
}

for n in errorcode:  # noqa : F405
    posix_error_mappings[os.strerror(n)] = n


def errno_from_msgb(err, map=posix_error_mappings, encoding="utf8", errors="ignore"):
    if err:
        error = err.rsplit(b":", 1)[-1].strip()
    else:
        return default_errorno
    return map.get(error.decode(encoding, errors=errors), default_errorno)


def errno_create_localized_mapping(lang):
    try:
        _ = gettext.translation("libc", languages=[lang])
        _ = _.gettext
    except FileNotFoundError as e:
        warnings.warn(f"Using default mapping for language {lang}: {str(e)}")
        return posix_error_mappings

    localized_map = dict(posix_error_mappings)

    for k, v in posix_error_mappings.items():
        localized_map[_(k)] = v

    return localized_map
