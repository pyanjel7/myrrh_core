import myrrh.core.services

__name__ = myrrh.core.services.__distname__.upper() + " Development Framework"

__doc__ = """
    current version: %(version)s

%(summary)s

%(full_description)s

License
=======

%(license)s

""" % {
    "summary": myrrh.core.services.cfg_get(section="@metadata@", key="Summary"),
    "version": myrrh.core.services.__version__,
    "full_description": myrrh.core.services.cfg_get(section="@metadata@", key="Description"),
    "license": myrrh.core.services.__license__,
}

__docformat__ = "restructuredtext"
