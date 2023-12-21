# -*- coding: utf-8 -*-

import os
import errno
import tempfile
import threading

from myrrh.core.interfaces import abstractmethod
from myrrh.core.services import PID, cfg_init
from myrrh.core.services.system import AbcRuntime, FileException, _mlib_
from ..mpython import _mosfs

__mlib__ = "AbcAdvFs"


class AdvFsFile:
    def __init__(self, arg):
        self.arg = arg
        self._file = None

    def __enter__(self):
        self._file = self.open()
        return self._file

    def __exit__(self, *a, **kwa):
        self.close()

    def close(self):
        if self._file:
            self._file.close()
            self._file = None


class AdvFsFileW(AdvFsFile):
    def open(self):
        if self.arg is None:
            return tempfile.SpooledTemporaryFile()

        if hasattr(self.arg, "write"):
            return self.arg

        return open(self.arg, "wb")


class AdvFsFileR(AdvFsFile):
    def open(self):
        if hasattr(self.arg, "read"):
            return self.arg

        return open(self.arg, "rb")


class AdvFsFileGet(AdvFsFile):
    def __init__(self, system: AbcRuntime, path, size, header=b""):
        super().__init__((system, path, size))

        self.system = system
        self.path = path
        self._thread = threading.Thread(target=self._run)

        self.rfile, self.wfile = system.myrrh_syscall.open_pipe()
        self.rfile, self.wfile = system.myrrh_syscall.gethandle(self.rfile), system.myrrh_syscall.gethandle(self.wfile)  # type: ignore[assignment]

        self.header = header

    def _run(self):
        if self.header:
            sz = 0
            while sz < len(self.header):
                sz += self.wfile.write(self.header[sz:])
        try:
            self.system.myrrh_syscall.stream_in(self.path, self.wfile)
        finally:
            self.wfile.close()

    def open(self):
        self._thread.start()
        return self.rfile

    def close(self):
        self._thread.join()
        super().close()


class AbcAdvFs(AbcRuntime):
    __frameworkpath__ = "mfs.advfs"

    CHUNK_SZ = cfg_init("advfs_file_chunk_size", 1024 * 500, section="myrrh.framework.mfs")
    COPY_BUFSIZE = cfg_init("advfs_copy_buffer_size", 1024 * 64, section="myrrh.framework.mfs")

    @property
    def os(self):
        return _mlib_(_mosfs)(self)

    @abstractmethod
    def _mkdirs(self, dirs: list):
        pass

    @abstractmethod
    def _chunk_header(self, file_descs):
        pass

    @abstractmethod
    def _unchunk(self, path):
        pass

    @abstractmethod
    def _write_chunk(self, path, file_descs):
        pass

    @abstractmethod
    def _scanfiles(self, files):
        """
        return files(path, size)
        """

    @abstractmethod
    def _scantree(self, path):
        """
        return dirs(path), files(path, size)
        """

    def scanfiles(self, files):
        """
        return files(path, size)
        """
        _cast_ = (self.myrrh_os.fdcast(f) for f in files)
        files = (self.myrrh_os.p(f) for f in files)
        files = self._scanfiles(files)

        return [_c_(f) for _c_, (f, _) in zip(_cast_, files)], [sz for (f, sz) in files]

    def scantree(self, path):
        """
        return dirs(path), files(path, size)
        """
        _cast_ = self.myrrh_os.fdcast(path)
        path = self.myrrh_os.p(path)

        root = path if path.endswith(self.myrrh_os.sepb) else path + self.myrrh_os.sepb
        root = self.myrrh_os.getpathb(root)

        dirs, files = self._scantree(path)

        dirs = (d[len(root) + 1 :] if d.startswith(root) else d for d in dirs)

        _files = []
        _szs = []
        for f, sz in files:
            _files.append(f[len(root) + 1 :] if f.startswith(root) else f)
            _szs.append(sz)

        return [_cast_(d) for d in dirs], [_cast_(f) for f in _files], _szs

    def local_scantree(self, path):
        dirs = []
        files = []
        sizes = []

        path = path if path[-1] == os.sep else path + os.sep

        def _scan(path):
            with os.scandir(path) as scan:
                for ent in scan:
                    yield ent
                    if ent.is_dir():
                        yield from _scan(ent.path)

        for ent in _scan(path):
            ent_path = ent.path[len(path) :] if ent.path.startswith(path) else ent.path
            if ent.is_dir():
                dirs.append(ent_path)
            else:
                files.append(ent_path)
                sizes.append(os.path.getsize(os.path.join(path, ent_path)))

        return dirs, files, sizes

    def trpath(self, path):
        def _trpath(path):
            _cast_ = self.myrrh_os.fdcast(path)
            path = self.myrrh_os.p(path)

            if self.myrrh_os._sepb_ == b"\\":
                path = path.replace(b"/", self.myrrh_os._sepb_)
            else:
                path = path.replace(b"\\", self.myrrh_os._sepb_)

            return _cast_(path)

        if isinstance(path, list):
            return list(_trpath(p) for p in path)

        if isinstance(path, tuple):
            return tuple(_trpath(p) for p in path)

        return _trpath(path)

    def _local_write_chunk(self, stream, file_descs):
        stream.write(self._chunk_header(file_descs))

        for src, _, _ in file_descs:
            with AdvFsFileR(src) as f:
                self.copyfileobj(f, stream)

    def _chunk_file_name(self, chunk_nb=None, chunk_name=None):
        if chunk_nb is None:
            return b"%d%d%s" % (PID, id(self), self.myrrh_os.cfg.uuid.encode())

        if chunk_name:
            return b"%s%d.chunk" % (chunk_name, chunk_nb)

        return b"%d%d%s%d.chunk" % (
            PID,
            id(self),
            self.myrrh_os.cfg.uuid.encode(),
            chunk_nb,
        )

    def _local_makechunks(self, srcs, dests, sizes, chunk_size, chunk_name=None):
        # return src, dest, ischunk, file_descs
        nb_chunk = 0
        file_descs = []
        total_sz = 0

        tempdir = self.myrrh_os.tmpdirb

        for file_desc in zip(srcs, dests, sizes):
            src, dest, size = file_desc

            if size is None:
                FileException(self, errno=errno.ENOENT, filename=src).raised()

            if size > chunk_size:
                yield src, dest, False, [file_desc]

            elif total_sz + size < chunk_size:
                file_descs.append(file_desc)

            else:
                chunkpath = self.myrrh_os.joinpath(tempdir, self._chunk_file_name(nb_chunk, chunk_name=chunk_name))
                try:
                    stf = tempfile.SpooledTemporaryFile()
                    self._local_write_chunk(stf, file_descs)
                    stf.seek(0)
                    yield stf, chunkpath, True, file_descs
                    nb_chunk += 1
                finally:
                    stf.close()

                file_descs = [file_desc]

        # only one file, direct download

        if len(file_descs) == 1:
            src, dest, size = file_descs[0]
            yield src, dest, False, file_descs

        elif file_descs:
            try:
                chunkpath = self.myrrh_os.joinpath(tempdir, self._chunk_file_name(nb_chunk, chunk_name=chunk_name))
                stf = tempfile.SpooledTemporaryFile()
                self._local_write_chunk(stf, file_descs)
                stf.seek(0)
                yield stf, chunkpath, True, file_descs
            finally:
                stf.close()

    def _makechunks(self, srcs, dests, sizes, chunk_size, chunk_name=None):
        # return src, dest, ischunk, file_descs
        nb_chunk = 0
        file_descs = []
        total_sz = 0

        tempdir = self.myrrh_os.tmpdirb

        for file_desc in zip(srcs, dests, sizes):
            src, dest, size = file_desc

            if size is None:
                FileException(self, errno=errno.ENOENT, filename=src).raised()

            if size > chunk_size:
                yield src, dest, False, [file_desc]

            elif total_sz + file_desc[2] < chunk_size:
                file_descs.append(file_desc)
            else:
                chunkpath = self.myrrh_os.joinpath(tempdir, self._chunk_file_name(nb_chunk, chunk_name=chunk_name))
                self._write_chunk(chunkpath, file_descs)
                yield chunkpath, None, True, file_descs
                nb_chunk += 1
                file_descs = [file_desc]

        # only one file, direct transfer

        if len(file_descs) == 1:
            src, dest, size = file_descs[0]
            yield src, dest, False, file_descs

        elif file_descs:
            chunkpath = self.myrrh_os.joinpath(tempdir, self._chunk_file_name(nb_chunk, chunk_name=chunk_name))
            self._write_chunk(chunkpath, file_descs)
            yield chunkpath, None, True, file_descs

    def copyfileobj(self, fsrc, fdst, sz=0, length=0):
        """copy data from file-like object fsrc to file-like object fdst"""
        # Localize variable access to minimize overhead.
        if not length:
            length = self.COPY_BUFSIZE
        rd_sz = 0
        while not sz or rd_sz < sz:
            to_rd = min(sz - rd_sz, length) if sz else length
            buf = fsrc.read(to_rd)
            if not buf:
                break
            fdst.write(buf)
            rd_sz += len(buf)

        return rd_sz

    def mkdirs(self, dirs):
        dirs.sort()

        filtered_dirs = []
        for i in range(0, len(dirs) - 1):
            if not dirs[i] in dirs[i + 1]:
                filtered_dirs.append(self.myrrh_os.sh_escape_bytes(self.myrrh_os.p(dirs[i])))
        if dirs:
            filtered_dirs.append(self.myrrh_os.sh_escape_bytes(self.myrrh_os.p(dirs[-1])))

        self._mkdirs(filtered_dirs)

    def getfiles(
        self,
        src_files,
        dest_files=[],
        *,
        sizes=None,
        chunk_size=CHUNK_SZ,
        ignore_overwrite=False,
    ):
        result = []

        if not dest_files:
            dest_files = [os.path.join(os.getcwd(), self.basename(f)) for f in src_files]

        if len(src_files) != len(dest_files):
            raise ValueError("number of elements in source file list and destination path list must be equal")

        if not ignore_overwrite:
            for f in dest_files:
                if dest_files.count(f) != 1:
                    raise ValueError(f"destination {f} file already exists")

        if not chunk_size:
            for src, dest in zip(src_files, dest_files):
                src = self.myrrh_os.p(src)

                with AdvFsFileW(dest) as f:
                    self.myrrh_syscall.stream_in(src, f)
                    result.append(dest)

            return result

        if not sizes:
            _, sizes = self.scanfiles(src_files)

        for src, dest, ischunk, file_descs in self._makechunks(src_files, dest_files, sizes, chunk_size):
            with AdvFsFileW(dest) as stream:
                self.myrrh_syscall.stream_in(os.fsencode(src), stream)

                if ischunk:
                    stream.seek(0)
                    for _, dest, sz in file_descs:
                        with AdvFsFileW(dest) as f:
                            self.copyfileobj(stream, f, sz)

            result.extend(d for _, d, _ in file_descs)

        return result

    def getfile(self, src, dest=""):
        dests = [] if not dest else [dest]
        return self.getfiles([src], dests, chunk_size=0)

    def getdir(self, src, dest="", *, chunk_size=CHUNK_SZ):
        if not dest:
            dest = os.getcwd()

        dirs, files, sizes = self.scantree(src)

        if os.path.isdir(dest) or dest.endswith(os.sep):
            dest = os.path.join(dest, self.myrrh_os.basename(src))
            os.makedirs(dest, exist_ok=True)

        for d in dirs:
            dir = os.path.join(dest, *d.split(self.myrrh_os.sepb.decode()))
            os.makedirs(dir, exist_ok=True)

        return dirs, self.getfiles(
            [self.myrrh_os.joinpath(src, f) for f in files],
            [os.path.join(dest, *f.split(self.myrrh_os.sepb.decode())) for f in files],
            sizes=sizes,
            chunk_size=chunk_size,
        )

    def pushfiles(self, src_files, dest_files=[], *, sizes=None, chunk_size=CHUNK_SZ):
        if not dest_files:
            dest_files = [self.myrrh_os.joinpath(self.myrrh_os._getcwdb_(), os.basename(f)) for f in src_files]

        if len(src_files) != len(dest_files):
            raise ValueError("number of elements in source file list and destination path list must be equal")

        result = []
        if not chunk_size:
            for src, dest in zip(src_files, dest_files):
                with AdvFsFileR(src) as f:
                    self.myrrh_syscall.stream_out(self.myrrh_os.fsencode(dest), f)
                    result.append(dest)

            return result

        if not sizes:
            sizes = []
            for f in src_files:
                sizes.append(os.path.getsize(f))

        for src, dest, merged, file_descs in self._local_makechunks(src_files, dest_files, sizes, chunk_size=chunk_size):
            with AdvFsFileR(src) as stream:
                self.myrrh_syscall.stream_out(os.fsencode(dest), stream)
            if merged:
                self._unchunk(dest)

            result.extend(d for _, d, _ in file_descs)

        return result

    def pushfile(self, src, dest=""):
        if self.myrrh_os.fs.is_container(self.myrrh_os.fsencode(dest)):
            dest = self.myrrh_os.joinpath(dest, os.path.basename(src))

        dests = [] if not dest else [dest]

        return self.pushfiles([src], dests, chunk_size=0)

    def pushdir(self, src, dest="", *, chunk_size=CHUNK_SZ):
        if not dest:
            dest = self.myrrh_os.fsdecode(self.myrrh_os._getcwdb_())

        dirs, files, sizes = self.local_scantree(src)
        dirs = [self.myrrh_os.joinpath(*d.split(os.sep)) for d in dirs]

        if dest.endswith(self.myrrh_os.sepb.decode()) or self.myrrh_os.fs.is_container(self.myrrh_os.p(dest)):
            dest = self.myrrh_os.joinpath(dest, os.path.basename(src))

        self.mkdirs([self.myrrh_os.joinpath(dest, d) for d in dirs])

        files = self.pushfiles(
            [os.path.join(src, f) for f in files],
            [self.myrrh_os.joinpath(dest, *f.split(os.sep)) for f in files],
            sizes=sizes,
            chunk_size=chunk_size,
        )

        return dirs, files

    def trmod(self, srcpath, destpath, mode=-1):
        self.myrrh_os.p = self.myrrh_os.p(destpath)
        srcpath = os.fsencode(srcpath)

        fmode = mode if mode != -1 else ("%o" % os.stat(srcpath).st_mode)[-3:] if os.name == self.myrrh_os.cfg.os else self.default_mode

        if fmode != -1:
            self.chmod(fmode, destpath)

    def transferfiles(self, entity, src_files, dest_files=[], *, sizes=None, chunk_size=CHUNK_SZ):
        result = []

        entity = AbcAdvFs(entity.system)

        if not dest_files:
            dest_files = [entity.myrrh_os.basename(f) for f in src_files]

        if len(src_files) != len(dest_files):
            raise ValueError("number of elements in source file list and destination path list must be equal")

        if sizes is None:
            _, sizes = entity.scanfiles(src_files)

        if len(src_files) != len(sizes):
            raise ValueError("number of elements in source file list and associated size list differs")

        dest_files = [self.trpath(d) for d in dest_files]

        if not chunk_size:
            for src, dest, sz in zip(src_files, dest_files, sizes):
                if sz is None:
                    FileException(entity, errno=errno.ENOENT, filename=src).raised()

                with AdvFsFileGet(entity, entity.myrrh_os.p(src), sz) as f:
                    self.myrrh_syscall.stream_out(self.myrrh_os.fsencode(dest), f)
                result.append(dest)

            return result

        target_tempdir = self.myrrh_os.tmpdirb
        for src, dest, ischunk, file_descs in entity._makechunks(src_files, dest_files, sizes, chunk_size, chunk_name=self._chunk_file_name()):
            header = self._chunk_header(file_descs) if ischunk else b""
            size = sum(sz for _, _, sz in file_descs)

            with AdvFsFileGet(entity, entity.myrrh_os.p(src), size, header) as stream:
                if dest is None:
                    dest = self.myrrh_os.joinpath(
                        target_tempdir,
                        entity.myrrh_os.p(entity.myrrh_os.basename(src) + b"_"),
                    )
                self.myrrh_syscall.stream_out(self.myrrh_os.fsencode(dest), stream)

                if ischunk:
                    self._unchunk(dest)

            if ischunk:
                entity.rm(src)

            result.extend(d for _, d, _ in file_descs)

        return result

    def transferfile(self, entity, src, dest=""):
        if dest and self.myrrh_os.fs.is_container(dest):
            dest = self.myrrh_os.joinpath(dest, entity.runtime.myrrh_os.basename(src))

        dests = [] if not dest else [dest]
        return self.transferfiles(entity, [src], dests, chunk_size=0)

    def transferdir(self, entity, src, dest="", *, chunk_size=CHUNK_SZ):
        e_advfs = AbcAdvFs(entity.system)

        _cast_ = e_advfs.myrrh_os.fdcast(src)

        src = e_advfs.myrrh_os.p(src)
        dest = self.myrrh_os.p(dest)

        if not dest:
            dest = self.myrrh_os.getpathb()

        if self.myrrh_os.fs.is_container(dest) or dest.endswith(self.myrrh_os.sepb):
            dest = self.myrrh_os.joinpath(dest, e_advfs.myrrh_os.fsencode(e_advfs.myrrh_os.basename(src)))

        dirs, files, sizes = e_advfs.scantree(src)

        self.mkdirs(
            list(
                map(
                    lambda d: self.myrrh_os.joinpath(dest, self.myrrh_os.fsencode(self.trpath(d))),
                    dirs,
                )
            )
        )
        files = self.transferfiles(
            entity,
            [e_advfs.myrrh_os.joinpath(src, f) for f in files],
            [self.myrrh_os.joinpath(dest, self.myrrh_os.fsencode(f)) for f in files],
            sizes=sizes,
            chunk_size=chunk_size,
        )

        return [_cast_(d) for d in dirs], [_cast_(f) for f in files]

    def transfer(self, entity, src, dest="", *, chunk_size=CHUNK_SZ):
        if entity.runtime.myrrh_os.fs.is_container(src):
            return self.transferdir(entity, src, dest, chunk_size=chunk_size)

        return [], self.transferfile(entity, src, dest=dest)

    def copy(self, srcs, dest):
        """
        copy dirs or files entries to other location on the entity

        if dest is a directory src is copy inside dest
        """
        dest = self.myrrh_os.p(dest)

        srcs = [self.myrrh_os.p(src) for src in srcs] if isinstance(srcs, (list, tuple)) else [self.myrrh_os.p(srcs)]

        self._localtransfer(srcs, dest)

    @abstractmethod
    def _localtransfer(self, src, dest):
        """
        copy dirs or files entries to other location on the entity

        if dest is a directory src is copy inside dest
        """

    def move(self, srcs, dest):
        """
        move dirs or files entries to other location on the entity

        if dest is a directory src is copy inside dest
        """
        dest = self.myrrh_os.p(dest)

        srcs = [self.myrrh_os.p(src) for src in srcs] if isinstance(srcs, (list, tuple)) else [self.myrrh_os.p(srcs)]

        self._localmove(srcs, dest)

    @abstractmethod
    def _localmove(self, src, dest):
        ...

    def rm(self, srcs):
        """
        remove complete directory trees or files entries
        """
        srcs = [self.myrrh_os.p(src) for src in srcs] if isinstance(srcs, (list, tuple)) else [self.myrrh_os.p(srcs)]

        self._localremove(srcs)

    @abstractmethod
    def _localremove(self, srcs):
        ...


AdvFs = AbcAdvFs
