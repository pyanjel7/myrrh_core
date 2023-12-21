# -*- coding: utf-8 -*-

import unittest
import cProfile
import pstats
import os

import os as localos
import io as localio
import test.support.os_helper as localsupport
import tempfile as localtempfile

import bmy

from myrrh.utils import mstring


from myrrh.utils.myrrh_test_init import *  # noqa: F403

main = "main"
if main not in bmy.eids():
    # By default, we use a local entity
    main = bmy.new(path="**/local", eid="main")


tgt = "tgt"
if tgt not in bmy.eids():
    tgt = bmy.new(path="**/local", eid="tgt")

setUp(f"bmy.{os.path.basename(__file__)}", eid=("tgt", "main"))  # noqa: F405

with bmy.select("tgt"):
    from mlib.py import os as tgtos
    from mlib.py import tempfile as tgttempfile
    from mlib.py.test.support import os_helper as tgtsupport

with bmy.select(main):
    from mlib.py import os, tempfile
    from mlib.fs import advfs
    from mlib.py.test.support import os_helper as support

bmy.select(main)

local_open = open


def read_dist(path, entity):
    with localio.BytesIO() as buf:
        with bmy.select(entity) as entity:
            from mlib.py import os

        path = path.replace("\\", os.sep).replace("/", os.sep)
        entity.runtime.myrrh_syscall.stream_in(os.fsencode(path), buf)
        return buf.getbuffer().tobytes()


class BMyrrhstProfile(unittest.TestCase):
    def setUp(self):
        self.total = None
        self.pr = cProfile.Profile()

    def tearDown(self):
        if self.total:
            print(
                "%s in %s/s"
                % (
                    mstring.hr_size(self.total),
                    mstring.hr_size(self.total / pstats.Stats(self.pr).total_tt),
                )
            )


class SetupDirLocal(BMyrrhstProfile):
    def setUp(self):
        super().setUp()

        join = localos.path.join
        self.addCleanup(localsupport.rmtree, localsupport.TESTFN)
        open = local_open

        # Build:
        #     TESTFN/
        #       TEST1/              a file kid and two directory kids
        #         tmp1
        #         SUB1/             a file kid and a directory kid
        #           tmp2
        #           SUB11/          no kids
        #         SUB2/             a file kid and a directory kid
        #           tmp3
        #           SUB21/
        #             tmp5
        #       TEST2/
        #         tmp4              a lone file
        self.walk_path = join(localsupport.TESTFN, "TEST1")
        self.sub1_path = join(self.walk_path, "SUB1")
        self.sub11_path = join(self.sub1_path, "SUB11")
        sub2_path = join(self.walk_path, "SUB2")
        sub21_path = join(sub2_path, "SUB 21")
        tmp1_path = join(self.walk_path, "tmp1")
        tmp2_path = join(self.sub1_path, "tmp2")
        tmp3_path = join(sub2_path, "tmp3")
        tmp5_path = join(sub21_path, "tmp5")
        self.link_path = join(sub2_path, "link")
        t2_path = join(localsupport.TESTFN, "TEST2")
        tmp4_path = join(localsupport.TESTFN, "TEST2", "tmp4")
        tmp6_path = join(localsupport.TESTFN, "TEST2", "tmp6")

        self.dirs = [
            self.walk_path,
            self.sub1_path,
            self.sub11_path,
            sub2_path,
            sub21_path,
            t2_path,
        ]

        # Create stuff.
        for d in self.dirs:
            localos.makedirs(d)

        self.files = [tmp1_path, tmp2_path, tmp3_path, tmp4_path, tmp5_path]
        self.filecontents = {}
        for path in self.files:
            d = b"You've got the " + path.encode() + b"file. This file is autogenerated by the myrrh project.\n"
            self.filecontents[localos.path.basename(path)] = {"data": d, "size": len(d)}

        d = b"\0" * advfs.CHUNK_SZ + b"You've got the " + tmp6_path.encode() + b"file. This file is autogenerated by the myrrh project.\n"

        self.filecontents[localos.path.basename(tmp6_path)] = {
            "data": d,
            "size": len(d),
        }
        self.files.append(tmp6_path)

        for path in self.files:
            with open(path, "bx") as f:
                f.write(self.filecontents[localos.path.basename(path)]["data"])

    def assertFiles(self, files, data):
        for d, file in zip(data, files):
            self.assertEqual(d, self.filecontents[file]["data"])

    def assertSizes(self, files, sizes):
        for file, size in zip(files, sizes):
            self.assertEqual(size, self.filecontents[localos.path.basename(file)]["size"])

    def assertDirs(self, dirs):
        for d in self.dirs:
            self.assertIn(advfs.trpath(d[len(support.TESTFN) + 1 :]), advfs.trpath(dirs))


class SetupDirEntity(BMyrrhstProfile):
    def setUp(self):
        super().setUp()

        join = os.path.join
        self.addCleanup(support.rmtree, support.TESTFN)

        # Build:
        #     TESTFN/
        #       TEST1/              a file kid and two directory kids
        #         tmp1
        #         SUB1/             a file kid and a directory kid
        #           tmp2
        #           SUB11/          no kids
        #         SUB2/             a file kid and a directory kid
        #           tmp3
        #           SUB21/
        #             tmp5
        #       TEST2/
        #         tmp4              a lone file
        self.walk_path = join(support.TESTFN, "TEST1")
        self.sub1_path = join(self.walk_path, "SUB1")
        self.sub11_path = join(self.sub1_path, "SUB11")
        sub2_path = join(self.walk_path, "SUB2")
        sub21_path = join(sub2_path, "SUB 21")
        tmp1_path = join(self.walk_path, "tmp1")
        tmp2_path = join(self.sub1_path, "tmp2")
        tmp3_path = join(sub2_path, "tmp3")
        tmp5_path = join(sub21_path, "tmp5")
        self.link_path = join(sub2_path, "link")
        t2_path = join(support.TESTFN, "TEST2")
        tmp4_path = join(support.TESTFN, "TEST2", "tmp4")
        tmp6_path = join(support.TESTFN, "TEST2", "tmp6")

        self.dirs = [
            self.walk_path,
            self.sub1_path,
            self.sub11_path,
            sub2_path,
            sub21_path,
            t2_path,
        ]

        # Create stuff.
        for d in self.dirs:
            os.makedirs(d)

        self.files = [tmp1_path, tmp2_path, tmp3_path, tmp4_path, tmp5_path]
        self.filecontents = {}
        for path in self.files:
            d = b"You've got the " + path.encode() + b"file. This file is autogenerated by the myrrh project.\n"
            self.filecontents[os.path.basename(path)] = {"data": d, "size": len(d)}

        d = b"\0" * advfs.CHUNK_SZ + b"You've got the " + path.encode() + b"file. This file is autogenerated by the myrrh project.\n"

        self.filecontents[os.path.basename(tmp6_path)] = {"data": d, "size": len(d)}
        self.files.append(tmp6_path)

        for path in self.files:
            bmy.entity().runtime.myrrh_syscall.stream_out(
                os.fsencode(path),
                localio.BytesIO(self.filecontents[os.path.basename(path)]["data"]),
            )

    def assertFiles(self, files, data):
        for d, file in zip(data, files):
            self.assertEqual(d, self.filecontents[file]["data"], "file %s not match" % file)

    def assertSizes(self, files, sizes):
        for file, size in zip(files, sizes):
            self.assertEqual(size, self.filecontents[os.path.basename(file)]["size"])

    def assertDirs(self, dirs):
        for d in self.dirs:
            self.assertIn(d[len(support.TESTFN) + 1 :], dirs)


class TestBmyGet(SetupDirEntity):
    def test_getfile(self):
        files = []
        data = []

        for file in self.files:
            dest = localtempfile.mktemp(dir=os.getcwd())
            with self.pr:
                bmy.get(file, dest)

            files.append(os.path.basename(file))
            with local_open(dest, "rb") as f:
                data.append(f.read())

        self.assertFiles(files, data)

        self.total = sum(len(d) for d in data)

    def test_getdir(self):
        tempdir = localtempfile.mkdtemp()
        self.addCleanup(localsupport.rmtree, tempdir + localos.sep)

        with self.pr:
            dirs, files = bmy.get(support.TESTFN, tempdir + localos.sep)

        self.assertEqual(len(files), len(self.files))

        for f in files:
            self.assertTrue(f.find(support.TESTFN))

        data = []
        for file in files:
            with local_open(file, "rb") as f:
                data.append(f.read())

        self.assertFiles((localos.path.basename(f) for f in files), data)
        self.assertDirs(dirs)

        self.total = sum(len(d) for d in data)

    def test_getdir_nochunk(self):
        tempdir = localtempfile.mkdtemp()
        self.addCleanup(localsupport.rmtree, tempdir + localos.sep)

        with self.pr:
            dirs, files = bmy.get(support.TESTFN, tempdir + localos.sep, chunk_size=0)

        self.assertEqual(len(files), len(self.files))

        for f in files:
            self.assertTrue(f.find(support.TESTFN))

        data = []
        for file in files:
            with local_open(file, "rb") as f:
                data.append(f.read())

        self.assertFiles((localos.path.basename(f) for f in files), data)
        self.assertDirs(dirs)

        self.total = sum(len(d) for d in data)

    def test_getdir_rename(self):
        tempdir = localtempfile.mkdtemp()
        self.addCleanup(localsupport.rmtree, tempdir)

        with self.pr:
            dirs, files = bmy.get(localsupport.TESTFN, os.path.join(tempdir, "notcreated"))

        self.assertEqual(len(files), len(self.files))

        for f in files:
            self.assertTrue(f.find(localsupport.TESTFN) == -1)

        data = []
        for file in files:
            with local_open(file, "rb") as f:
                data.append(f.read())

        self.assertFiles((localos.path.basename(f) for f in files), data)
        self.assertDirs(dirs)

        self.total = sum(len(d) for d in data)

    def test_getdir_existing_dir(self):
        tempdir = localtempfile.mkdtemp()
        self.addCleanup(localsupport.rmtree, tempdir)

        with self.pr:
            dirs, files = bmy.get(localsupport.TESTFN, tempdir)

        self.assertEqual(len(files), len(self.files))

        for f in files:
            self.assertTrue(f.find(localsupport.TESTFN))

        data = []
        for file in files:
            with local_open(file, "rb") as f:
                data.append(f.read())

        self.assertFiles((localos.path.basename(f) for f in files), data)
        self.assertDirs(dirs)

        self.total = sum(len(d) for d in data)


class TestBmyPush(SetupDirLocal):
    def test_pushfile(self):
        files = []
        data = []
        self.pr = cProfile.Profile()
        for file in self.files:
            dest = tempfile.mktemp(dir=os.getcwd())

            with self.pr:
                ds, fs = bmy.push(file, dest)
                self.assertEqual(len(ds), 0)
                self.assertEqual(fs, [dest])

            files.append(localos.path.basename(file))
            data.append(read_dist(dest, bmy.entity()))

        self.assertFiles(files, data)

        self.total = sum(len(d) for d in data)

    def test_pushdir_nochunk(self):
        tempdir = tempfile.mkdtemp(dir=os.getcwd())
        self.addCleanup(support.rmtree, tempdir + os.sep)

        with self.pr:
            dirs, files = bmy.push(localsupport.TESTFN, tempdir + os.sep, chunk_size=0)

        self.assertEqual(len(files), len(self.files))

        for f in files:
            self.assertTrue(f.find(localsupport.TESTFN))

        data = []
        for file in files:
            data.append(read_dist(file, bmy.entity()))

        self.assertFiles((os.path.basename(f) for f in files), data)
        self.assertDirs(dirs)

        self.total = sum(len(d) for d in data)

    def test_pushdir(self):
        tempdir = tempfile.mkdtemp(dir=os.getcwd())
        self.addCleanup(support.rmtree, tempdir + os.sep)

        with self.pr:
            dirs, files = bmy.push(localsupport.TESTFN, tempdir + os.sep)

        self.assertEqual(len(files), len(self.files))

        for f in files:
            self.assertTrue(f.find(localsupport.TESTFN))

        data = []
        for file in files:
            data.append(read_dist(file, bmy.entity()))

        self.assertFiles((os.path.basename(f) for f in files), data)
        self.assertDirs(dirs)

        self.total = sum(len(d) for d in data)

    def test_pushdir_rename(self):
        tempdir = tempfile.mkdtemp(dir=os.getcwd())
        self.addCleanup(support.rmtree, tempdir)

        with self.pr:
            dirs, files = bmy.push(localsupport.TESTFN, os.path.join(tempdir, "notcreated"))

        self.assertEqual(len(files), len(self.files))

        for f in files:
            self.assertTrue(f.find(localsupport.TESTFN) == -1)

        data = []
        for file in files:
            data.append(read_dist(file, bmy.entity()))

        self.assertFiles((os.path.basename(f) for f in files), data)
        self.assertDirs(dirs)

        self.total = sum(len(d) for d in data)

    def test_pushdir_existing_dir(self):
        tempdir = tempfile.mkdtemp(dir=os.getcwd())
        self.addCleanup(support.rmtree, tempdir)

        with self.pr:
            dirs, files = bmy.push(localsupport.TESTFN, tempdir)

        self.assertEqual(len(files), len(self.files))

        for f in files:
            self.assertTrue(f.find(localsupport.TESTFN))

        data = []
        for file in files:
            data.append(read_dist(file, bmy.entity()))

        self.assertFiles((os.path.basename(f) for f in files), data)
        self.assertDirs(dirs)

        self.total = sum(len(d) for d in data)


class TestBmyTransfer(SetupDirEntity):
    def test_transferfile(self):
        files = []
        data = []

        self.files = [self.files[5]]

        for file in self.files:
            dest = tgttempfile.mktemp(dir=tgtos.getcwd())

            with self.pr:
                bmy.transfer(main, file, dest, eid=tgt)

            files.append(os.path.basename(file))
            data.append(read_dist(dest, tgt))

        self.assertFiles(files, data)

        self.total = sum(len(d) for d in data)

    def test_transferdir_nochunk(self):
        tempdir = tgttempfile.mkdtemp(dir=tgtos.getcwd())
        self.addCleanup(tgtsupport.rmtree, tempdir + tgtos.sep)

        with self.pr:
            dirs, files = bmy.transfer(main, support.TESTFN, tempdir + tgtos.sep, chunk_size=0, eid=tgt)

        self.assertEqual(len(files), len(self.files))

        for f in files:
            self.assertTrue(f.find(support.TESTFN))

        data = []
        for file in files:
            data.append(read_dist(file, tgt))

        self.assertFiles((tgtos.path.basename(f) for f in files), data)
        self.assertDirs(dirs)

        self.total = sum(len(d) for d in data)

    def test_transferdir(self):
        tempdir = tgttempfile.mkdtemp(dir=tgtos.getcwd())
        self.addCleanup(tgtsupport.rmtree, tempdir + tgtos.sep)

        with self.pr:
            dirs, files = bmy.transfer(main, support.TESTFN, tempdir + tgtos.sep, eid=tgt)

        self.assertEqual(len(files), len(self.files))

        for f in files:
            self.assertTrue(f.find(support.TESTFN))

        data = []
        for file in files:
            data.append(read_dist(file, tgt))

        self.assertFiles((tgtos.path.basename(f) for f in files), data)
        self.assertDirs(dirs)

        self.total = sum(len(d) for d in data)

    def test_transferdir_rename(self):
        tempdir = tgttempfile.mkdtemp(dir=tgtos.getcwd())
        self.addCleanup(tgtsupport.rmtree, tempdir)

        with self.pr:
            dirs, files = bmy.transfer(main, support.TESTFN, tgtos.path.join(tempdir, "notcreated"), eid=tgt)

        self.assertEqual(len(files), len(self.files))

        for f in files:
            self.assertTrue(f.find(support.TESTFN) == -1)

        data = []
        for file in files:
            data.append(read_dist(file, tgt))

        self.assertFiles((localos.path.basename(f) for f in files), data)
        self.assertDirs(dirs)

        self.total = sum(len(d) for d in data)

    def test_transferdir_existing_dir(self):
        tempdir = tgttempfile.mkdtemp(dir=tgtos.getcwd())
        self.addCleanup(tgtsupport.rmtree, tempdir)

        with self.pr:
            dirs, files = bmy.transfer(main, support.TESTFN, tempdir, eid=tgt)

        self.assertEqual(len(files), len(self.files))

        for f in files:
            self.assertTrue(f.find(support.TESTFN))

        data = []
        for file in files:
            data.append(read_dist(file, tgt))

        self.assertFiles((tgtos.path.basename(f) for f in files), data)
        self.assertDirs(dirs)

        self.total = sum(len(d) for d in data)


"""
def load_tests(*args):
    tests = (TestBmyPush,
             TestBmyGet,
             TestBmyTransfer)
    suite = unittest.TestSuite([unittest.makeSuite(test, prefix='test_') for test in tests])
    return suite
"""

if __name__ == "__main__":
    unittest.main(verbosity=2)