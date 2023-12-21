# -*- coding: utf-8 -*-
import unittest
import bmy

from myrrh.core.services.groups import MyrrhGroup


class TestBuild(unittest.TestCase):
    def setUp(self):
        bmy.init()

    def test_build1(self):
        e1 = bmy.new(path="**/local", eid="e1")
        self.assertEqual(bmy.current(e1), e1)
        bmy.build(eid=e1)
        self.assertTrue(bmy.isbuilt(eid=e1))
        e2 = bmy.new(path="**/local", eid="e2")
        bmy.build(eid=e2)
        self.assertTrue(bmy.isbuilt(eid=e2))

    def test_buildn(self):
        e1 = bmy.new(path="**/local", eid="e1")
        self.assertEqual(bmy.current(e1), e1)
        bmy.build(eid=(e1,))
        self.assertTrue(bmy.isbuilt(eid=e1))
        e2 = bmy.new(path="**/local", eid="e2")
        bmy.build(eid=(e2,))
        self.assertTrue(bmy.isbuilt(eid=e2))
        e3 = bmy.new(path="**/local", eid="e3")
        e4 = bmy.new(path="**/local", eid="e4")
        e34 = bmy.build(eid=(e3, e4))
        self.assertTrue(bmy.isbuilt(eid=e2))
        self.assertTrue(bmy.isbuilt(eid=e34))

    def test_build_eid(self):
        e1 = bmy.new(path="**/local", eid="e1")
        e2 = bmy.new(path="**/local", eid="e2")
        bmy.build(eid=e2)
        self.assertTrue(bmy.isbuilt(eid=e2))
        self.assertFalse(bmy.isbuilt(eid=e1))
        bmy.build(eid=e1)
        self.assertTrue(bmy.isbuilt(eid=e1))


class TestBmyEntity(unittest.TestCase):
    def test_basic_entity(self):
        eids = bmy.new(path="**/local", eid=("e1", "e2"))
        bmy.build(eid=eids)
        es = bmy.entity(eid=eids)

        self.assertIsInstance(es, MyrrhGroup)


class TestBmyNew(unittest.TestCase):
    def test_basic_new_setting(self):
        eid = bmy.new(path="**/local", cwd="doesnotexist", eid="e1")
        self.assertRaises(bmy.BmyMyrrhFailure, bmy.build, eid=eid)


if __name__ == "__main__":
    unittest.main(verbosity=2)
