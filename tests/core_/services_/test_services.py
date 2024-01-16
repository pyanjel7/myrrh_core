import unittest


class TestServices(unittest.TestCase):
    def basic_test(self):
        from myrrh.core import services

        services.rebase()
