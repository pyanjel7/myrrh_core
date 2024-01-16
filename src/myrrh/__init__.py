import pkg_resources
import os

__distname__ = "myrrh"


PID = os.getpid()


def myrrh_versioning(file, dist_name):
    try:
        # try to find version from package dist
        version = pkg_resources.get_distribution(dist_name).version
    except Exception:
        version = "0.0.0"

    if version == "0.0.0":
        # try to find version from scm
        try:
            from setuptools_scm import get_version  # type: ignore[import-not-found]

            return get_version(relative_to=file)
        except Exception:
            pass

    return version


try:
    from .__license__ import copyright as __copyright__, license as __license__
except Exception:
    __copyright__ = ""
    __license__ = ""

try:
    from .__version__ import version as __version__
except Exception:
    __version__ = myrrh_versioning(__file__, __distname__)
