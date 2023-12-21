import unittest
import logging
import os

import bmy

from myrrh.core.services import log
from myrrh.utils.myrrh_test_init import setUp

setUp(f"bmy.{os.path.basename(__file__)}")


class Test_basic(unittest.TestCase):
    def test_info(self):
        i = bmy.info()
        for k in (
            "id",
            "description",
            "location",
            "os",
            "services",
            "catalog",
            "cwd",
            "warehouse",
        ):
            self.assertIn(k, i)
        i = bmy.info("id.id")
        self.assertIsInstance(i, str)
        i = bmy.info("notvalid.wiz")
        self.assertEqual(str(i), "na")

    def test_debug(self):
        current_level = bmy.debug()
        try:
            bmy.debug("DEBUG")
            self.assertEqual(log.level, logging.DEBUG)
            bmy.debug("INFO")
            self.assertEqual(log.level, logging.INFO)
            bmy.debug(logging.CRITICAL)
            self.assertEqual(log.level, logging.CRITICAL)
        finally:
            bmy.debug(current_level)

    def test_save_load(self):
        import os

        try:
            bmy.save("test_entity.emyrrh")
            self.assertTrue(os.path.isfile("test_entity.emyrrh"))
            bmy.load("test_entity.emyrrh")

            bmy.save("test_entity_full.emyrrh", full=True)
            e2 = bmy.load("test_entity_full.emyrrh")
            bmy.build(eid=e2)
            self.assertEqual(bmy.info("warehouse.id.uuid", eid=e2), bmy.info("warehouse.id.uuid"))
            self.assertTrue(os.path.isfile("test_entity_full.emyrrh"))

        finally:
            os.remove("test_entity.emyrrh")
            os.remove("test_entity_full.emyrrh")

    def test_which(self):
        cmd = bmy.info("warehouse.system.shell")

        p = bmy.which(bmy.info("warehouse.system.shell"))

        try:
            p.index(cmd)
        except ValueError:
            self.fail("{cmd} not found in path returns by which")

    def test_launch_kill(self):
        pid = bmy.launch("ping 127.0.0.1")
        bmy.kill(pid)


if __name__ == "__main__":
    unittest.main()
