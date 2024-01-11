from myrrh.core.services.config import __distname__, __version__, __license__, cfg_get

__name__ = __distname__.upper() + " Development Framework"

__doc__ = f"""
    current version: {__version__}

{cfg_get(section="@metadata@", key="Summary")}

{cfg_get(section="@metadata@", key="Description")}

License
=======

{__license__}

"""

__docformat__ = "restructuredtext"
