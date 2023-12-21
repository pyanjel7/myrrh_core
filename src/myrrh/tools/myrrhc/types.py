# flake8: noqa: F401

import re

from click.types import BOOL, FLOAT, INT, UNPROCESSED, UUID, ParamType, STRING, Choice


class RegExType(ParamType):
    def __init__(self, reg):
        self.creg = re.compile(reg)

    def convert(self, value, param, ctx):
        result = self.creg.match(value)
        if not result:
            self.fail('"%s" invalid expression' % value, param, ctx)

        return result
