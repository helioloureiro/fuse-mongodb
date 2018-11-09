#!/usr/bin/env python3

# Based on fioc.py from Cedreic Carree <beg0@free.fr>
#
#    This program can be distributed under the terms of the GNU LGPL.
#

import os, sys, stat, errno
from errno import *
from stat import *
import fcntl
# pull in some spaghetti to make this stuff work without fuse-py being installed
try:
    import _find_fuse_parts
except ImportError:
    pass
import fuse
from fuse import Fuse
import syslog
import fusemongolib
import time

PYTHON_MAJOR_MINOR = "%s.%s" % (sys.version_info[0], sys.version_info[1])

if sys.version_info[0] != 3:
    raise RuntimeError("Use python3.  Your current python version is: %s" % PYTHON_MAJOR_MINOR)


if not hasattr(fuse, '__version__'):
    raise RuntimeError("your fuse-py doesn't know of fuse.__version__, probably it's too old.")

fuse.fuse_python_api = (0, 2)

fuse.feature_assert('stateful_files', 'has_init')

def debug(message):
    syslog.syslog(syslog.LOG_NOTICE, message)

def flag2mode(flags):
    md = {os.O_RDONLY: 'r', os.O_WRONLY: 'w', os.O_RDWR: 'w+'}
    m = md[flags & (os.O_RDONLY | os.O_WRONLY | os.O_RDWR)]

    if flags | os.O_APPEND:
        m = m.replace('w', 'a', 1)

    return m

class PyFuseMongoStat(fuse.Stat):
    def __init__(self):
        syslog.syslog(syslog.LOG_NOTICE, "MyStat.__init__()")
        now = int(time.time())
        self.st_mode = stat.S_IFREG | 0o666
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 1
        self.st_uid = os.getuid()
        self.st_gid = os.getgid()
        self.st_size = 0
        self.st_atime = now
        self.st_mtime = now
        self.st_ctime = now

    def stat_result(self):
        return os.stat_result((self.st_mode,
                               self.st_ino,
                               self.st_dev,
                               self.st_nlink,
                               self.st_uid,
                               self.st_gid,
                               self.st_size,
                               self.st_atime,
                               self.st_mtime,
                               self.st_ctime))
    def stat(self):
        return self.st_mode, \
            self.st_ino,     \
            self.st_dev,     \
            self.st_nlink,   \
            self.st_uid,     \
            self.st_gid,     \
            self.st_size,    \
            self.st_atime,   \
            self.st_mtime,   \
            self.st_ctime

    def __iter__(self):
        return (self.stat())

    def __str__(self):
        return "os.stat_result(st_mode=%d" % self.st_mode + \
            ", st_ino=%d"   % self.st_ino   + \
            ", st_dev=%d"   % self.st_dev   + \
            ", st_nlink=%d" % self.st_nlink + \
            ", st_uid=%d"   % self.st_uid   + \
            ", st_gid=%d"   % self.st_gid   + \
            ", st_size=%d"  % self.st_size  + \
            ", st_atime=%d" % self.st_atime + \
            ", st_mtime=%d" % self.st_mtime + \
            ", st_ctime=%d" % self.st_ctime + ")"

class PyFuseMongo(Fuse):

    def __init__(self, *args, **kw):
        debug("PyFuseMongo.__init__()")

        Fuse.__init__(self, *args, **kw)

        # do stuff to set up your filesystem here, if you want
        #import thread
        #thread.start_new_thread(self.mythread, ())
        self.root = '/'
        self.mongo = fusemongolib.MongoInterface()
        self.path = None
        self.listing = self.mongo.list_files()
        now = int(time.time())
        self.stat = PyFuseMongoStat()


    def mongo_stat(self, path):
        syslog.syslog(syslog.LOG_NOTICE, "PyFuseMongo.mongo_stat()")
        if self.path == path:
            # no actions needed
            return self.stat
        syslog.syslog(syslog.LOG_NOTICE, " * mongo_stat(): path=%s" % path)
        self.path = path
        filename = path[1:] # removes the "/" at the beginning
        syslog.syslog(syslog.LOG_NOTICE, " * mongo_stat(): filename=%s" % filename)
        if not filename in self.listing:
            if filename == "." or filename == ".." or path == "/":
                objpath = PyFuseMongoStat()
                objpath.st_mode = stat.S_IFDIR | 0o755
                objpath.st_nlink = 2
                syslog.syslog(syslog.LOG_NOTICE, " * mongo_stat(): returning new path obj for path=%s" % path)
                syslog.syslog(syslog.LOG_NOTICE, " * mongo_stat(): %s" % objpath.__str__())
                return objpath
            syslog.syslog(syslog.LOG_NOTICE, " * mongo_stat(): returning -ENOENT for path=%s" % path)
            return -errno.ENOENT
        obj = self.mongo.search_db(filename)
        if obj is None:
            objpath = PyFuseMongoStat()
            objpath.st_mode = stat.S_IFDIR | 0o755
            objpath.st_nlink = 2
            syslog.syslog(syslog.LOG_NOTICE, " * mongo_stat(): EMPTY object")
            generic = PyFuseMongoStat()
            syslog.syslog(syslog.LOG_NOTICE, " * mongo_stat(): %s" % objpath.__str__())
            return objpath
        permission = obj['permission']
        syslog.syslog(syslog.LOG_NOTICE, " * mongo_stat(): permission=%d" % permission)
        uid = obj['uid']
        syslog.syslog(syslog.LOG_NOTICE, " * mongo_stat(): uid=%d" % uid)
        gid = obj['gid']
        syslog.syslog(syslog.LOG_NOTICE, " * mongo_stat(): gid=%d" % gid)
        content = obj['content']
        st_size = len(content)
        syslog.syslog(syslog.LOG_NOTICE, " * mongo_stat(): st_size=%d" % st_size)
        date_time = obj['date']
        st_ctime = date_time.timestamp()
        syslog.syslog(syslog.LOG_NOTICE, " * mongo_stat(): st_ctime=%f" % st_ctime)
        syslog.syslog(syslog.LOG_NOTICE, " * mongo_stat(): date=%s" % time.ctime(st_ctime))
        self.stat.st_mode = stat.S_IFREG | permission
        self.stat.st_ino = 0
        self.stat.st_dev = 0
        self.stat.st_nlink = 1
        self.stat.st_uid = uid
        self.stat.st_gid = gid
        self.stat.st_size = st_size
        self.stat.st_atime = st_ctime
        self.stat.st_mtime = st_ctime
        self.stat.st_ctime = st_ctime
        """
        >>> import os
        >>> os.lstat("/etc/passwd")
        os.stat_result(st_mode=33188, st_ino=1051825, st_dev=64769, st_nlink=1, st_uid=0, st_gid=0, st_size=3255, st_atime=1541669084, st_mtime=1541409883, st_ctime=1541409883)
        >>> x = os.lstat("/etc/passwd")
        >>> x.st_mode
        33188
        >>> x
        os.stat_result(st_mode=33188, st_ino=1051825, st_dev=64769, st_nlink=1, st_uid=0, st_gid=0, st_size=3255, st_atime=1541669084, st_mtime=1541409883, st_ctime=1541409883)
        """
        syslog.syslog(syslog.LOG_NOTICE, " * mongo_stat(): %s" % self.stat.__str__())
        return self.stat


#    def mythread(self):
#
#        """
#        The beauty of the FUSE python implementation is that with the python interp
#        running in foreground, you can have threads
#        """
#        print "mythread: started"
#        while 1:
#            time.sleep(120)
#            print "mythread: ticking"

    def getattr(self, path):
        debug("PyFuseMongo.getattr()")
        #return os.lstat("." + path)
        return self.mongo_stat(path)

    def readlink(self, path):
        debug("PyFuseMongo.readlink()")
        return os.readlink("." + path)

    def readdir(self, path, offset):
        debug("PyFuseMongo.readdir()")
        debug(" * readdir(): path=%s" % path)
        debug(" * readdir(): offset=%d" % offset)
        #for e in os.listdir("." + path):
        #    yield fuse.Direntry(e)
        all_files = [ ".", ".." ]
        all_files += self.listing
        for e in all_files:
            yield fuse.Direntry(e)

    def unlink(self, path):
        debug("PyFuseMongo.unlink()")
        os.unlink("." + path)

    def rmdir(self, path):
        debug("PyFuseMongo.rmdir()")
        os.rmdir("." + path)

    def symlink(self, path, path1):
        debug("PyFuseMongo.symlink()")
        os.symlink(path, "." + path1)

    def rename(self, path, path1):
        debug("PyFuseMongo.rename()")
        os.rename("." + path, "." + path1)

    def link(self, path, path1):
        debug("PyFuseMongo.link()")
        os.link("." + path, "." + path1)

    def chmod(self, path, mode):
        debug("PyFuseMongo.chmod()")
        os.chmod("." + path, mode)

    def chown(self, path, user, group):
        debug("PyFuseMongo.chown()")
        os.chown("." + path, user, group)

    def truncate(self, path, len):
        debug("PyFuseMongo.truncate()")
        f = open("." + path, "a")
        f.truncate(len)
        f.close()

    def mknod(self, path, mode, dev):
        debug("PyFuseMongo.mknod()")
        os.mknod("." + path, mode, dev)

    def mkdir(self, path, mode):
        debug("PyFuseMongo.mkdir()")
        os.mkdir("." + path, mode)

    def utime(self, path, times):
        debug("PyFuseMongo.utime()")
        os.utime("." + path, times)

#    The following utimens method would do the same as the above utime method.
#    We can't make it better though as the Python stdlib doesn't know of
#    subsecond preciseness in acces/modify times.
#
#    def utimens(self, path, ts_acc, ts_mod):
#      os.utime("." + path, (ts_acc.tv_sec, ts_mod.tv_sec))

    def access(self, path, mode):
        debug("PyFuseMongo.access()")
        if not os.access("." + path, mode):
            return -EACCES

#    This is how we could add stub extended attribute handlers...
#    (We can't have ones which aptly delegate requests to the underlying fs
#    because Python lacks a standard xattr interface.)
#
#    def getxattr(self, path, name, size):
#        val = name.swapcase() + '@' + path
#        if size == 0:
#            # We are asked for size of the value.
#            return len(val)
#        return val
#
#    def listxattr(self, path, size):
#        # We use the "user" namespace to please XFS utils
#        aa = ["user." + a for a in ("foo", "bar")]
#        if size == 0:
#            # We are asked for size of the attr list, ie. joint size of attrs
#            # plus null separators.
#            return len("".join(aa)) + len(aa)
#        return aa

    def statfs(self):
        debug("PyFuseMongo.statfs()")
        """
        Should return an object with statvfs attributes (f_bsize, f_frsize...).
        Eg., the return value of os.statvfs() is such a thing (since py 2.2).
        If you are not reusing an existing statvfs object, start with
        fuse.StatVFS(), and define the attributes.

        To provide usable information (ie., you want sensible df(1)
        output, you are suggested to specify the following attributes:

            - f_bsize - preferred size of file blocks, in bytes
            - f_frsize - fundamental size of file blcoks, in bytes
                [if you have no idea, use the same as blocksize]
            - f_blocks - total number of blocks in the filesystem
            - f_bfree - number of free blocks
            - f_files - total number of file inodes
            - f_ffree - nunber of free file inodes
        """

        return os.statvfs(".")

    def fsinit(self):
        debug("PyFuseMongo.fsinit()")
        #os.chdir(self.root)

    class PyFuseMongoFile(object):

        def __init__(self, path, flags, *mode):
            debug("PyFuseMongoFile.__init__()")
            self.file = os.fdopen(os.open("." + path, flags, *mode),
                                  flag2mode(flags))
            self.fd = self.file.fileno()

        def read(self, length, offset):
            debug("PyFuseMongoFile.read()")
            self.file.seek(offset)
            return self.file.read(length)

        def write(self, buf, offset):
            debug("PyFuseMongoFile.write()")
            self.file.seek(offset)
            self.file.write(buf)
            return len(buf)

        def release(self, flags):
            debug("PyFuseMongoFile.release()")
            self.file.close()

        def _fflush(self):
            debug("PyFuseMongoFile._fflush()")
            if 'w' in self.file.mode or 'a' in self.file.mode:
                self.file.flush()

        def fsync(self, isfsyncfile):
            debug("PyFuseMongoFile.fsync()")
            self._fflush()
            if isfsyncfile and hasattr(os, 'fdatasync'):
                os.fdatasync(self.fd)
            else:
                os.fsync(self.fd)

        def flush(self):
            debug("PyFuseMongoFile.flush()")
            self._fflush()
            # cf. xmp_flush() in fusexmp_fh.c
            os.close(os.dup(self.fd))

        def fgetattr(self):
            debug("PyFuseMongoFile.fgetattr()")
            return os.fstat(self.fd)

        def ftruncate(self, len):
            debug("PyFuseMongoFile.ftruncate()")
            self.file.truncate(len)

        def lock(self, cmd, owner, **kw):
            debug("PyFuseMongoFile.lock()")
            # The code here is much rather just a demonstration of the locking
            # API than something which actually was seen to be useful.

            # Advisory file locking is pretty messy in Unix, and the Python
            # interface to this doesn't make it better.
            # We can't do fcntl(2)/F_GETLK from Python in a platfrom independent
            # way. The following implementation *might* work under Linux.
            #
            # if cmd == fcntl.F_GETLK:
            #     import struct
            #
            #     lockdata = struct.pack('hhQQi', kw['l_type'], os.SEEK_SET,
            #                            kw['l_start'], kw['l_len'], kw['l_pid'])
            #     ld2 = fcntl.fcntl(self.fd, fcntl.F_GETLK, lockdata)
            #     flockfields = ('l_type', 'l_whence', 'l_start', 'l_len', 'l_pid')
            #     uld2 = struct.unpack('hhQQi', ld2)
            #     res = {}
            #     for i in xrange(len(uld2)):
            #          res[flockfields[i]] = uld2[i]
            #
            #     return fuse.Flock(**res)

            # Convert fcntl-ish lock parameters to Python's weird
            # lockf(3)/flock(2) medley locking API...
            op = { fcntl.F_UNLCK : fcntl.LOCK_UN,
                   fcntl.F_RDLCK : fcntl.LOCK_SH,
                   fcntl.F_WRLCK : fcntl.LOCK_EX }[kw['l_type']]
            if cmd == fcntl.F_GETLK:
                return -EOPNOTSUPP
            elif cmd == fcntl.F_SETLK:
                if op != fcntl.LOCK_UN:
                    op |= fcntl.LOCK_NB
            elif cmd == fcntl.F_SETLKW:
                pass
            else:
                return -EINVAL

            fcntl.lockf(self.fd, op, kw['l_start'], kw['l_len'])


    def main(self, *a, **kw):
        debug("PyFuseMongo.main()")

        self.file_class = self.PyFuseMongoFile

        return Fuse.main(self, *a, **kw)


def main():
    debug("main()")
    usage = """
Userspace mongodb as filesystem.

""" + Fuse.fusage

    server = PyFuseMongo(version="%prog " + fuse.__version__,
                 usage=usage,
                 dash_s_do='setsingle')

    server.parser.add_option(mountopt="root", metavar="PATH", default='/',
                             help="mirror filesystem from under PATH [default: %default]")
    server.parse(values=server, errex=1)

    try:
        if server.fuse_args.mount_expected():
            os.chdir(server.root)
    except OSError:
        print("can't enter root of underlying filesystem", file=sys.stderr)
        sys.exit(1)

    server.main()


if __name__ == '__main__':
    syslog.openlog("fuse-mongodb")
    main()
    syslog.closelog()
