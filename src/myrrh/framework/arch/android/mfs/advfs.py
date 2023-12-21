from myrrh.framework.mfs.madvfs import AbcAdvFs
from myrrh.core.services.system import ExecutionFailureCauseRVal

__mlib__ = "AdvFs"


class AdvFs(AbcAdvFs):
    default_mode = 0o777

    CHUNK_HEADER_SCRIPT = b"""\
path=$0
exec 0<"$path"
while IFS= read -r f; do
case $f in
"exit")
echo exit
break;
esac
done
read szs
read files
splitter()
{
IFS=:
set $files
for s in $szs ; do
dd of="$1" count=$s iflag=count_bytes
shift
done
}
splitter
rm -f "$path"
exit"""

    def chown(self, path, user, group):
        path = self.myrrh_os.shencode(path)
        user = self.myrrh_os.shencode(user)
        group = self.myrrh_os.shencode(group)
        _, _, rval = self.myrrh_os.shell.execute(b"/bin/chown %s:%s %s" % (user, group, path))
        return rval == 0

    def chmod(self, mode, path):
        path = self.myrrh_os.shencode(path)
        _, _, rval = self.myrrh_os.shell.execute(b"/bin/chmod %o %s" % (mode, path))
        return rval == 0

    def _localtransfer(self, srcs, dest):
        srcs = [b"'%s'" % src for src in srcs]
        srcs = b" ".join(srcs)

        _, err, rval = self.myrrh_os.cmdb(
            b"%(cp)s -a -f %(srcs)s %(dest)s",
            srcs=srcs,
            dest=dest and self.myrrh_os.sh_escape_bytes(dest) or b".",
        )
        if b"non-directory" in err:
            err = b"Not a directory"

        ExecutionFailureCauseRVal(self, err, rval, 0).check()

    def _localmove(self, srcs, dest):
        if len(srcs) > 1:
            srcs = b" ".join((self.myrrh_os.sh_escape_bytes(s) for s in srcs))
            _, err, rval = self.myrrh_os.cmdb(
                b"if [ -d '%(dest)s' ] ; then %(mv)s %(srcs)s '%(dest)s'; else exit 10; fi",
                srcs=srcs,
                dest=self.myrrh_os.sh_escape_bytes(dest),
            )
        else:
            _, err, rval = self.myrrh_os.cmdb(
                b"%(mv)s %(srcs)s %(dest)s",
                srcs=self.myrrh_os.sh_escape_bytes(srcs[0]),
                dest=self.myrrh_os.sh_escape_bytes(dest),
            )

        ExecutionFailureCauseRVal(self, err, rval, 0).check()

    def _localremove(self, srcs):
        srcs = b" ".join((self.myrrh_os.sh_escape_bytes(s) for s in srcs))
        _, err, rval = self.myrrh_os.cmdb(b"%(rm)s -Rf %(srcs)s", srcs=srcs)

        ExecutionFailureCauseRVal(self, err, rval, 0).check()

    def _chunk_header(self, file_descs, *, destdir=None):
        szs = (str(f[2]).encode() for f in file_descs)
        paths = (self.myrrh_os.p(f[1]) for f in file_descs)
        return b"\n".join((self.CHUNK_HEADER_SCRIPT, b":".join(szs), b":".join(paths))) + b"\n"

    def _unchunk(self, path):
        path = self.myrrh_os.p(path)
        _, e, r = self.myrrh_os.cmdb(b"%(sh)s %(path)s", path=self.myrrh_os.sh_escape_bytes(path))
        ExecutionFailureCauseRVal(self, e, r, 0).check()

    def _write_chunk(self, path, file_descs):
        path = self.myrrh_os.p(path)
        files = b" ".join((b"%s" % self.myrrh_os.sh_escape_bytes(self.myrrh_os.p(file)) for file, _, _ in file_descs))
        _, e, r = self.myrrh_os.cmdb(
            b'%(cat)s %(files)s > "%(path)s"',
            files=files,
            path=self.myrrh_os.sh_escape_bytes(path),
        )
        ExecutionFailureCauseRVal(self, e, r, 0).check()

    def _mkdirs(self, dirs: list):
        cmd = b'for d in %(dirs)s; do %(mkdir)s -p "$d"; done'

        dirs: bytes = b" ".join(dirs)
        _, e, r = self.myrrh_os.cmdb(cmd, dirs=dirs)
        ExecutionFailureCauseRVal(self, e, r, 0).check()

    def _scanfiles(self, files):
        """
        return files(path, size)
        """
        result = []
        for f in files:
            stat = self.myrrh_os.fs.stat(f)
            result.append((f, stat.st_size))

        return result

    def _scantree(self, path):
        dirs = []
        files = []

        def _loop(startpath=None):
            paths = self.myrrh_os.fs.list(startpath or path)
            for p, i in paths:
                p = self.myrrh_os.joinpath(paths.cname, p)
                if paths.is_container(i):
                    dirs.append(p)
                    _loop(p)
                else:
                    files.append((p, paths.size(i)))

        _loop()

        return dirs, files
