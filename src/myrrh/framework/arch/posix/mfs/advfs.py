from myrrh.utils import mstring
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
dd of="$1" count=$s bs=1
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
        srcs = [self.myrrh_os.sh_escape_bytes(src) for src in srcs]
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

        dirs = b" ".join(dirs)
        _, e, r = self.myrrh_os.cmdb(cmd, dirs=dirs)
        ExecutionFailureCauseRVal(self, e, r, 0).check()

    def _scanfiles(self, files):
        """
        return files(path, size)
        """
        files = b" ".join((b"%s" % self.myrrh_os.sh_escape_bytes(f) for f in files))
        o, e, r = self.myrrh_os.cmdb(b"%(find)s %(files)s -exec stat -c %%n:%%s {} \\;", files=files)
        ExecutionFailureCauseRVal(self, e, r, 0).check()

        output = (o.split(b":") for o in o.splitlines())

        files = []
        for path, sz in output:
            path = path.lstrip(b"./")
            if path and path != b".":
                files.append((self.myrrh_os.shdecode(path).encode(), mstring.str2intb(sz)))

        return files

    def _scantree(self, path):
        path = self.myrrh_os.p(path)

        o, e, r = self.myrrh_os.cmdb(b"%(find)s . -exec %(stat)s -c %%n:%%A:%%s {} \\;", execute_working_dir=path)
        ExecutionFailureCauseRVal(self, e, r, 0).check()

        output = (o.split(b":") for o in o.splitlines())

        dirs = []
        files = []
        for path, ty, sz in output:
            path = path.lstrip(b"./")

            if not path or path == b".":
                continue

            if ty.startswith(b"d"):
                dirs.append(self.myrrh_os.shdecode(path).encode())
            else:
                files.append((self.myrrh_os.shdecode(path).encode(), mstring.str2intb(sz)))

        return dirs, files
