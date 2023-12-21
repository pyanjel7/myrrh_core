import threading
import unittest
import mlib
import time


class _MLibTest(unittest.TestCase):
    def setUp(self):
        import bmy

        e1 = bmy.new(path="**/local", eid="e1")
        e2 = bmy.new(path="**/local", eid="e2")
        e3 = bmy.new(path="**/local", eid="e3")
        e4 = bmy.new(path="**/local", eid="e4")
        bmy.build(eid=e1)
        bmy.build(eid=e2)
        bmy.build(eid=e3)
        bmy.build(eid=e4)
        self.e1 = bmy.entity(e1).system
        self.e2 = bmy.entity(e2).system
        self.e3 = bmy.entity(e3).system
        self.e4 = bmy.entity(e4).system


class BasicTest(_MLibTest):
    def test_import(self):
        import sys

        import mlib
        import mlib.py
        import mlib.fs

        self.assertIs(sys.modules["mlib"], mlib)
        self.assertIs(sys.modules["mlib.py"], mlib.py)
        self.assertIs(sys.modules["mlib.fs"], mlib.fs)

    def test_select1(self):
        with mlib.mlib_select(self.e1):
            from mlib.py import os as os1

        with mlib.mlib_select(self.e2):
            from mlib.py import os as os2

        self.assertIsNot(os1, os2)
        self.assertEqual(os1.myrrh_os.cfg.id, self.e1.cfg.id)
        self.assertEqual(os2.myrrh_os.cfg.id, self.e2.cfg.id)

        from mlib.py import os

        self.assertIsNot(os, os1)
        self.assertIsNot(os, os2)

        from myrrh.core.interfaces import ABCDelegationMeta

        self.assertIsInstance(os, ABCDelegationMeta)

    def test_select_in_select(self):
        with mlib.mlib_select(self.e1):
            from mlib.py import os as os1

            with mlib.mlib_select(self.e2):
                from mlib.py import os as os2

        self.assertIsNot(os1, os2)
        self.assertEqual(os1.myrrh_os.cfg.id, self.e1.cfg.id)
        self.assertEqual(os2.myrrh_os.cfg.id, self.e2.cfg.id)

        from mlib.py import os

        self.assertIsNot(os, os1)
        self.assertIsNot(os, os2)

        from myrrh.core.interfaces import ABCDelegationMeta

        self.assertIsInstance(os, ABCDelegationMeta)


class TestWrappedModule(_MLibTest):
    def validate(self, os1, os2, osh1, osh2):
        self.assertIsNot(os1, os2)
        self.assertEqual(os1.myrrh_os.cfg.id, self.e1.cfg.id)
        self.assertEqual(os2.myrrh_os.cfg.id, self.e2.cfg.id)

        self.assertIsNot(self.e1, self.e2)
        self.assertIsNot(osh1, osh2)

        self.assertNotEqual(self.e1.cfg.id, self.e2.cfg.id)
        self.assertEqual(osh1.myrrh_os.cfg.id, self.e1.cfg.id)
        self.assertEqual(osh2.myrrh_os.cfg.id, self.e2.cfg.id)

        self.assertIsNot(osh1._mod, osh2._mod)
        self.assertEqual(osh1._mod.os.myrrh_os.cfg.id, self.e1.cfg.id)
        self.assertEqual(osh2._mod.os.myrrh_os.cfg.id, self.e2.cfg.id)

        cwd1 = os1.getcwd()
        cwd2 = os2.getcwd()

        with osh1.change_cwd(".."):
            self.assertNotEqual(cwd1, os1.getcwd())
            self.assertEqual(cwd2, os2.getcwd())

        self.assertEqual(cwd1, os1.getcwd())

    def test_select_with_os_helper(self):
        with mlib.mlib_select(self.e1):
            from mlib.py import os as os1
            from mlib.py.test.support import os_helper as osh1

        with mlib.mlib_select(self.e2):
            from mlib.py import os as os2
            from mlib.py.test.support import os_helper as osh2

        self.validate(os1, os2, osh1, osh2)

    def test_in_select_with_os_helper(self):
        with mlib.mlib_select(self.e1):
            from mlib.py.test.support import os_helper as osh1

            with mlib.mlib_select(self.e2):
                from mlib.py import os as os2
                from mlib.py.test.support import os_helper as osh2

            from mlib.py import os as os1

        self.validate(os1, os2, osh1, osh2)


class TestThreaded(_MLibTest):
    def validate(self, os1, osh1, e):
        self.assertEqual(os1.myrrh_os.cfg.id, e.cfg.id)

        self.assertEqual(osh1.myrrh_os.cfg.id, e.cfg.id)

        self.assertEqual(osh1._mod.os.myrrh_os.cfg.id, e.cfg.id)

        cwd1 = os1.getcwd()

        with osh1.change_cwd(".."):
            self.assertNotEqual(cwd1, os1.getcwd())
        self.assertEqual(cwd1, os1.getcwd())

    def _th1(self):
        for i in range(1, 100):
            with mlib.mlib_select(self.e1):
                from mlib.py import os

                time.sleep(0.1)
                from mlib.py.test.support import os_helper

                with mlib.mlib_select(self.e3):
                    from mlib.py import os as os3

                    time.sleep(0.1)
                    from mlib.py.test.support import os_helper as os_helper3

            self.validate(os, os_helper, self.e1)
            self.validate(os3, os_helper3, self.e3)

    def _th2(self):
        for i in range(1, 500):
            with mlib.mlib_select(self.e2):
                from mlib.py import os
                from mlib.py.test.support import os_helper

            with mlib.mlib_select(self.e4):
                from mlib.py import os as os4
                from mlib.py.test.support import os_helper as os_helper4

            self.validate(os, os_helper, self.e2)
            self.validate(os4, os_helper4, self.e4)

    def test_threading(self):
        th1 = threading.Thread(target=self._th1)
        th2 = threading.Thread(target=self._th2)

        th1.start()
        th2.start()

        th1.join()
        th2.join()


if __name__ == "__main__":
    unittest.main()
