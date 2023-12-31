# -*- coding: utf-8 -*-
import bmy
import unittest
import io as localio

import os

from myrrh.utils.myrrh_test_init import *  # noqa: F403

setUp(f"bmy.{os.path.basename(__file__)}")  # noqa: F405

with bmy.select():
    from mlib.py import os
    from mlib.py.test.support import os_helper


def read_dist(path, entity):
    with localio.BytesIO() as buf:
        with bmy.select(entity):
            from mlib.py import os

        path = path.replace("\\", os.sep).replace("/", os.sep)
        entity.runtime.myrrh_syscall.stream_in(os.fsencode(path), buf)
        return buf.getbuffer().tobytes()


class SetupDirEntity(unittest.TestCase):
    def setUp(self):
        super().setUp()

        join = os.path.join
        self.addCleanup(os_helper.rmtree, os_helper.TESTFN)

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
        self.walk_path = join(os_helper.TESTFN, "TEST1")
        self.sub1_path = join(self.walk_path, "SUB1")
        self.sub11_path = join(self.sub1_path, "SUB11")
        sub2_path = join(self.walk_path, "SUB2")
        sub21_path = join(sub2_path, "SUB 21")
        tmp1_path = join(self.walk_path, "tmp1")
        tmp2_path = join(self.sub1_path, "tmp2")
        tmp3_path = join(sub2_path, "tmp3")
        tmp5_path = join(sub21_path, "tmp5")
        self.link_path = join(sub2_path, "link")
        t2_path = join(os_helper.TESTFN, "TEST2")
        tmp4_path = join(os_helper.TESTFN, "TEST2", "tmp4")
        tmp6_path = join(os_helper.TESTFN, "TEST2", "tmp6")

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
            data = b"You've got the " + path.encode() + b"file. This file is autogenerated by the myrrh project.\n"
            self.filecontents[os.path.basename(path)] = {
                "data": data,
                "size": len(data),
            }

        data = b"\0" * 5000000 + b"You've got the " + tmp6_path.encode() + b"file. This file is autogenerated by the myrrh project.\n"

        self.filecontents[os.path.basename(tmp6_path)] = {
            "data": data,
            "size": len(data),
        }
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
            self.assertIn(d[len(os_helper.TESTFN) + 1 :], dirs)


class TestCp(SetupDirEntity):
    def test_cp_dest_is_dir(self):
        for d in self.dirs:
            dest_dir = bmy.joinpath(d, "cp")
            bmy.mkdir(dest_dir)

            for f in self.files:
                bmy.cp(f, dest_dir)
                stat_src = bmy.fstat(f)
                stat_dest = bmy.fstat(bmy.joinpath(dest_dir, bmy.basename(f)))
                self.assertEqual(stat_src["size"], stat_dest["size"])

    def test_cp_dest_is_new_name(self):
        for d in self.dirs:
            dest_dir = bmy.joinpath(d, "cp")
            bmy.mkdir(dest_dir)

            for f in self.files:
                dest_file = bmy.joinpath(dest_dir, bmy.basename(f) + "_cp")
                bmy.cp(f, dest_file)
                stat_src = bmy.fstat(f)
                stat_dest = bmy.fstat(dest_file)
                self.assertEqual(stat_src["size"], stat_dest["size"])

    def test_cp_dest_is_cwd(self):
        for d in self.dirs:
            dest_dir = bmy.joinpath(d, "cp")
            bmy.mkdir(dest_dir)

            for f in self.files:
                cwd = bmy.pwd()
                dest_dir = bmy.joinpath(cwd, d, "cp")
                bmy.mkdir(dest_dir)
                try:
                    f = bmy.abspath(f)
                    bmy.chdir(dest_dir)
                    bmy.cp(f)
                    stat_dest = bmy.fstat(f)
                    stat_src = bmy.fstat(bmy.joinpath(cwd, f))
                    self.assertEqual(stat_src["size"], stat_dest["size"])
                finally:
                    bmy.chdir(cwd)

    def test_cp_n_sources(self):
        cwd = bmy.pwd()
        for d in self.dirs:
            dest_dir = bmy.joinpath(cwd, d, "cp2")
            bmy.mkdir(dest_dir)

            bmy.cp(self.files, dest_dir)
            for f in self.files:
                stat_src = bmy.fstat(f)
                stat_dest = bmy.fstat(bmy.joinpath(dest_dir, bmy.basename(f)))
                self.assertEqual(stat_src["size"], stat_dest["size"])


class TestFs(SetupDirEntity):
    # 'edit', 'get', 'push', 'transfer',
    def test_chdir_pwd(self):
        cwd = bmy.pwd()
        for d in self.dirs:
            try:
                bmy.chdir(d)
                self.assertEqual(bmy.pwd(), bmy.joinpath(cwd, d))
            finally:
                bmy.chdir(cwd)

        for d in (bmy.abspath(d) for d in self.dirs):
            try:
                bmy.chdir(d)
                self.assertEqual(bmy.pwd(), bmy.joinpath(cwd, d))
            finally:
                bmy.chdir(cwd)

    def test_fstat(self):
        for f in self.files:
            bmy.fstat(f)

        for d in self.dirs:
            bmy.fstat(d)

    def test_lsdir(self):
        dirs = bmy.lsdir(os_helper.TESTFN)

        self.assertListEqual(dirs, ["TEST1", "TEST2"])

        self.assertRaises(NotADirectoryError, bmy.lsdir, self.files[0])

        dirs2 = bmy.lsdir(bmy.joinpath(self.dirs[0], "t*"))

        self.assertEqual(len(dirs2), 1)
        self.assertEqual(dirs2[0], bmy.joinpath(os_helper.TESTFN, "TEST1", "tmp1"))

    def test_mkdir(self):
        for d in self.dirs:
            path = bmy.joinpath(self.dirs[0], d)
            bmy.mkdir(path)
            stat = bmy.fstat(path)
            self.assertEqual(stat["file"], path)
            self.assertTrue(stat["access"].startswith("d"))


class TestRm(SetupDirEntity):
    def test_rm_file(self):
        for f in self.files:
            bmy.rm(f)
            self.assertRaises(FileNotFoundError, bmy.fstat, f)

    def test_rm_files(self):
        bmy.rm(self.files)
        for f in self.files:
            self.assertRaises(FileNotFoundError, bmy.fstat, f)

    def test_rm_dirs(self):
        bmy.rm(self.dirs)
        for d in self.dirs:
            self.assertRaises(FileNotFoundError, bmy.fstat, d)


class TestMove(SetupDirEntity):
    def test_move(self):
        path = bmy.joinpath(self.dirs[0], "moved")
        bmy.mkdir(path)
        for f in self.files:
            new_path = bmy.joinpath(path, bmy.basename(f) + "_moved")
            bmy.move(f, new_path)
            stat = bmy.fstat(new_path)
            self.assertEqual(stat["file"], new_path)

    def test_move_dest_is_dir_one_file(self):
        path = bmy.joinpath(self.dirs[0], "moved")
        bmy.mkdir(path)

        for f in self.files:
            new_path = bmy.joinpath(path, bmy.basename(f))
            bmy.move(f, path)
            stat = bmy.fstat(new_path)
            self.assertEqual(stat["file"], new_path)

    def test_move_dest_is_dir_many_files(self):
        path = bmy.joinpath(self.dirs[0], "moved")
        bmy.mkdir(path)
        bmy.move(self.files, path)

        for f in self.files:
            new_path = bmy.joinpath(path, bmy.basename(f))
            stat = bmy.fstat(new_path)
            self.assertEqual(stat["file"], new_path)


class TestReadWrite(SetupDirEntity):
    def test_read(self):
        data = []
        for f in self.files:
            data.append(bmy.read(f, binary=True))

        self.assertFiles((bmy.basename(f) for f in self.files), data)

    def test_write(self):
        for f, d in self.filecontents.items():
            bmy.write(bmy.joinpath(self.dirs[0], f), d["data"])

        for f, d in self.filecontents.items():
            data = bmy.read(bmy.joinpath(self.dirs[0], f), binary=True)
            self.assertEqual(data, d["data"])


if __name__ == "__main__":
    unittest.main()
