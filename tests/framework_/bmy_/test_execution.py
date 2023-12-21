# -*- coding: utf-8 -*-
import time
import bmy
import unittest

alt1 = "alt1"
if alt1 not in bmy.eids():
    # default using local entity
    alt1 = bmy.new(path="**/local", eid="alt1")

if not bmy.isbuilt(eid=alt1):
    bmy.build(eid=alt1)

main = "main"
if main not in bmy.eids():
    # default using local entity
    main = bmy.new(path="**/local", eid="main")

if not bmy.isbuilt(eid=main):
    bmy.build(eid=main)

bmy.select(main)

texts = ["ab", "a" * 1000]


class TestBmyExecute(unittest.TestCase):
    def test_execute_output(self):
        for text in texts:
            o, e, r = bmy.execute("echo %s" % text)
            self.assertEqual(r, 0)
            self.assertEqual(o.strip(), text)

        for text in texts:
            o, e, r = bmy.execute("echo %s >&2" % text)
            self.assertEqual(r, 0)
            self.assertEqual(e.strip(), text)

    def test_execute_exit_status(self):
        o, e, r = bmy.execute("exit 25")
        self.assertEqual(r, 25)

    def test_execute_count(self):
        count = 0
        for o, e, r in bmy.execute("echo loop", count=10):
            self.assertEqual(r, 0)
            self.assertEqual(o.strip(), "loop")
            count += 1

        self.assertEqual(count, 10)

        count = 0
        for o, e, r in bmy.execute("invalid command", count=10):
            self.assertNotEqual(r, 0)
            count += 1

        # infinite loop
        count = 0
        for o, e, r in bmy.execute("echo loop", count=-1, executein=False):
            self.assertEqual(r, 0)
            self.assertEqual(o.strip(), "loop")

            count += 1

            if count > 9:
                break

        self.assertEqual(count, 10)

    def test_execute_interval(self):
        st_time = 0
        for o, e, r in bmy.execute("echo loop", count=3, interval=5, executein=False):
            if st_time:
                end_time = time.monotonic()
                self.assertGreaterEqual(end_time - st_time, 5)
                self.assertGreaterEqual(10, end_time - st_time)
            self.assertEqual(o.strip(), "loop")
            st_time = time.monotonic()

    def test_execute_ttl(self):
        for text in texts:
            print(text)
            o, e, r = bmy.execute("echo %s" % text, ttl=10)
            self.assertEqual(r, 0)
            self.assertEqual(e.strip(), text)

    def test_execute_ttl2(self):
        exe = bmy.execute("ping 127.0.0.1", ttl=2, count=1)
        o, e, r = next(iter(exe))
        self.assertNotEqual(o.find("127.0.0.1"), -1)
