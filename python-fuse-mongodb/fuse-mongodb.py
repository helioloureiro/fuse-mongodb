#!/usr/bin/python3

# Based on fioc.py from Cedreic Carree <beg0@free.fr>
#
#    This program can be distributed under the terms of the GNU LGPL.
#
import os, stat, errno, struct
import syslog
from pymongo import MongoClient
import gridfs
import re
import sys
import random
import time, datetime
import mipsum
from errno import *
from stat import *
import fcntl


try:
    import _find_fuse_parts
except ImportError:
    pass
import fuse
from fuse import Fuse

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


# this mimics asm-generic/ioctl.h  header
# I'm not sure this is really portable, you'd better use ioctl-opt package or something similar
class IOCTL:
    _IOC_NRBITS = 8
    _IOC_TYPEBITS = 8
    _IOC_SIZEBITS = 14
    _IOC_DIRBITS = 2

    _IOC_NRMASK = (1 << _IOC_NRBITS)-1
    _IOC_TYPEMASK = (1 << _IOC_TYPEBITS)-1
    _IOC_SIZEMASK = (1 << _IOC_SIZEBITS)-1
    _IOC_DIRMASK = (1 << _IOC_DIRBITS)-1

    _IOC_NRSHIFT = 0
    _IOC_TYPESHIFT = _IOC_NRSHIFT + _IOC_NRBITS
    _IOC_SIZESHIFT = _IOC_TYPESHIFT + _IOC_TYPEBITS
    _IOC_DIRSHIFT = _IOC_SIZESHIFT + _IOC_SIZEBITS

    _IOC_NONE = 0
    _IOC_WRITE = 1
    _IOC_READ = 2

    @classmethod
    def _IOC(cls, d,t,nr,size):
        syslog.syslog(syslog.LOG_NOTICE, "IOCTL._IOC()")
        return (((d)  << cls._IOC_DIRSHIFT) |
            ((t) << cls._IOC_TYPESHIFT) | \
            ((nr)   << cls._IOC_NRSHIFT) | \
            ((size) << cls._IOC_SIZESHIFT))

    @classmethod
    def _IO(cls, t,nr):
        syslog.syslog(syslog.LOG_NOTICE, "IOCTL._IO()")
        return cls._IOC(cls._IOC_NONE, t, nr, 0)

    @classmethod
    def _IOR(cls, t,nr,size):
        syslog.syslog(syslog.LOG_NOTICE, "IOCTL._IOR()")
        return cls._IOC(cls._IOC_READ, t, nr, size)

    @classmethod
    def _IOW(cls, t,nr,size):
        syslog.syslog(syslog.LOG_NOTICE, "IOCTL._IOW()")
        return cls._IOC(cls._IOC_WRITE, t, nr, size)

    @classmethod
    def _IOWR(cls,t,nr,size):
        syslog.syslog(syslog.LOG_NOTICE, "IOCTL._IOWR()")
        return cls._IOC(cls._IOC_WRITE|cls._IOC_READ, t, nr, size)


# IOCTL (as defined in fioc.h)
# Note: on my system, size_t is an unsigned long
FIOC_GET_SIZE = IOCTL._IOR(ord('E'),0, struct.calcsize("L"));
FIOC_SET_SIZE = IOCTL._IOW(ord('E'),1, struct.calcsize("L"));

# object type
FIOC_NONE = 0
FIOC_ROOT = 1
FIOC_FILE = 2
FIOC_MONGO = 3

FIOC_NAME  = "mongodb"

class MongoDB:
    _server_url = 'mongodb://100.109.0.1:27017'

    def __init__(self):
        syslog.syslog(syslog.LOG_NOTICE, "MongoDB.__init__()")
        client = MongoClient(self._server_url)
        db = client.testdb
        self.xfs = db.xfs
        #self.fs = gridfs.GridFS(db)
        #self.fsb = gridfs.GridFSBucket(db)
        syslog.syslog(syslog.LOG_NOTICE, "MongoDB.__init__() ends")

    def list_files(self, directory=None):
        syslog.syslog(syslog.LOG_NOTICE, "MongoDB.list_files()")
        filenames = []
        for content in self.xfs.find():
            filepath = content['filename']
            #if directory is not None:
            #    filepath = re.sub("/mnt/mongodb", directory, filepath)
            filenames.append(filepath)
        return filenames

    def insert_file(self, filename, content):
        syslog.syslog(syslog.LOG_NOTICE, "MongoDB.insert_file()")
        syslog.syslog(syslog.LOG_NOTICE, " * filename=%s" % filename)
        json = {
            "filename" : filename,
            "content" : content,
            "date" : datetime.datetime.utcnow()
            }
        self.xfs.insert_one(json)

    def test_insert_db(self):
        syslog.syslog(syslog.LOG_NOTICE, "MongoDB.test_insert_db()")
        filename = "myfile-%d.txt" % random.randint(0,99999)
        m = mipsum.MussumLorum()
        text = "\n\n".join(m.get_paragraph())
        post = {"filename": filename,
                "content" : text,
                "date": datetime.datetime.utcnow()}

        post_id = self.xfs.insert_one(post)
        syslog.syslog(syslog.LOG_NOTICE, " test_insert_db(): post_id=%s" % post_id)
        return filename

    def search_db(self, filename):
        syslog.syslog(syslog.LOG_NOTICE, "MongoDB.search_db()")
        syslog.syslog(syslog.LOG_NOTICE, " * filename=%s" % filename)
        return self.xfs.find({ "filename" : filename })

    def test_delete_db(self, filename):
        syslog.syslog(syslog.LOG_NOTICE, "MongoDB.test_delete_db()")
        syslog.syslog(syslog.LOG_NOTICE, " * filename=%s" % filename)
        for entry in self.xfs.find({ "filename" : filename }):
            self.xfs.delete_one(entry)

    def test_populate_db(self):
        syslog.syslog(syslog.LOG_NOTICE, "MongoDB.test_populate_db()")
        counter = 10
        while counter > 0:
            self.test_insert_db()
            counter -= 1

    def test(self, directory=None):
        syslog.syslog(syslog.LOG_NOTICE, "MongoDB.test()")
        syslog.syslog(syslog.LOG_NOTICE, "MongoDB.__init__()")
        # insert
        print("inserting file...")
        filename = self.test_insert_db()
        print(" * file=%s inserted" % filename)

        # list filenames
        fs = self.list_files(directory)
        print("listing files:")
        for f in fs:
            print(" * %s" % f)

        # search
        print("test searching:")
        result = self.search_db(filename)
        print(" * found: %s" % result)

        # delete
        print("test delete:")
        self.test_delete_db(filename)
        print(" * filename=%s removed" % filename)


class XmpFile(object):

    def __init__(self, path, flags, *mode):
        debug("XmpFile.__init__()")
        self.file = os.fdopen(os.open("." + path, flags, *mode),
                                flag2mode(flags))
        self.fd = self.file.fileno()

    def read(self, length, offset):
        debug("XmpFile.read()")
        self.file.seek(offset)
        return self.file.read(length)

    def write(self, buf, offset):
        debug("XmpFile.write()")
        self.file.seek(offset)
        self.file.write(buf)
        return len(buf)

    def release(self, flags):
        debug("XmpFile.release()")
        self.file.close()

    def _fflush(self):
        debug("XmpFile._fflush()")
        if 'w' in self.file.mode or 'a' in self.file.mode:
            self.file.flush()

    def fsync(self, isfsyncfile):
        debug("XmpFile.fsync()")
        self._fflush()
        if isfsyncfile and hasattr(os, 'fdatasync'):
            os.fdatasync(self.fd)
        else:
            os.fsync(self.fd)

    def flush(self):
        debug("XmpFile.flush()")
        self._fflush()
        # cf. xmp_flush() in fusexmp_fh.c
        os.close(os.dup(self.fd))

    def fgetattr(self):
        debug("XmpFile.fgetattr()")
        return os.fstat(self.fd)

    def ftruncate(self, len):
        debug("XmpFile.ftruncate()")
        self.file.truncate(len)

    def lock(self, cmd, owner, **kw):
        debug("XmpFile.lock()")
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


class MyStat(fuse.Stat):
    def __init__(self):
        syslog.syslog(syslog.LOG_NOTICE, "MyStat.__init__()")
        now = int(time.time())
        self.st_mode = 0
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 0
        self.st_uid = 0
        self.st_gid = 0
        self.st_size = 0
        self.st_atime = now
        self.st_mtime = now
        self.st_ctime = now


class FiocFS(Fuse):

    def __init__(self, *args, **kw):
        syslog.syslog(syslog.LOG_NOTICE, "FiocFS.__init__()")
        Fuse.__init__(self, *args, **kw)
        self.mongo = MongoDB()
        self.mongo_files = self.mongo.list_files()
        self.buf =  ""
        syslog.syslog(syslog.LOG_NOTICE, "FiocFS.__init__() ends")

    def is_mongo(self, path):
        filename = path[1:]
        if filename in self.mongo_files:
            return True
        return False

    def resize(self, new_size):
        syslog.syslog(syslog.LOG_NOTICE, "FiocFS.resize()")
        old_size = len(self.buf)
        if new_size == old_size:
            return 0

        if new_size < old_size:
            self.buf = self.buf[0:new_size]
        else:
            self.buf = self.buf + "\x00" * (new_size - old_size)

        return 0

    def file_type(self, path):
        syslog.syslog(syslog.LOG_NOTICE, "FiocFS.file_type()")
        syslog.syslog(syslog.LOG_NOTICE, " * path=%s" % path)
        if self.is_mongo(path):
            syslog.syslog(syslog.LOG_NOTICE, " * file_type(): FIOC_MONGO")
            return FIOC_MONGO
        if not type(path) == str:
            syslog.syslog(syslog.LOG_NOTICE, " * file_type(): FIOC_ROOT")
            return FIOC_NONE
        if path == "/":
            syslog.syslog(syslog.LOG_NOTICE, " * file_type(): FIOC_ROOT")
            return FIOC_ROOT
        elif path == "/" + FIOC_NAME:
            syslog.syslog(syslog.LOG_NOTICE, " * file_type(): FIOC_FILE")
            return FIOC_FILE
        else:
            syslog.syslog(syslog.LOG_NOTICE, " * file_type(): FIOC_NONE")
            return FIOC_NONE

    def get_mongo_size(self, path):
        syslog.syslog(syslog.LOG_NOTICE, "FiocFS.get_mongo_size()")
        filename = path[1:] # removes the "/" at the beginning
        syslog.syslog(syslog.LOG_NOTICE, " * get_mongo_size(): filename=%s" % filename)
        obj = self.mongo.search_db(filename)[0]
        sizeof = len(obj['content'])
        del obj
        syslog.syslog(syslog.LOG_NOTICE, " * get_mongo_size(): sizeof=%d" % sizeof)
        return sizeof

    def get_mongo_ctime(self, path):
        syslog.syslog(syslog.LOG_NOTICE, "FiocFS.get_mongo_get_mongo_ctime()")
        filename = path[1:] # removes the "/" at the beginning
        syslog.syslog(syslog.LOG_NOTICE, " * get_mongo_get_mongo_ctime(): filename=%s" % filename)
        obj = self.mongo.search_db(filename)[0]
        dtime = obj['date']
        (syslog.LOG_NOTICE, " * get_mongo_ctime(): dtime=%s" % dtime)
        ctime = int(dtime.timestamp())
        del obj
        syslog.syslog(syslog.LOG_NOTICE, " * get_mongo_ctime(): ctime=%d" % ctime)
        return ctime

    def getattr(self, path):
        syslog.syslog(syslog.LOG_NOTICE, "FiocFS.getattr()")
        syslog.syslog(syslog.LOG_NOTICE, " * path=%s" % path)
        st = MyStat()
        ft = self.file_type(path)
        if ft == FIOC_ROOT:
            syslog.syslog(syslog.LOG_NOTICE, " * getattr(): FIOC_ROOT")
            st.st_mode = stat.S_IFDIR | 0o755
            st.st_nlink = 2
        elif ft == FIOC_FILE:
            syslog.syslog(syslog.LOG_NOTICE, " * getattr(): FIOC_FILE")
            st.st_mode = stat.S_IFREG | 0o666
            st.st_nlink = 1
            st.st_size = len(self.buf)
        elif ft == FIOC_MONGO:
            syslog.syslog(syslog.LOG_NOTICE, " * getattr(): FIOC_MONGO")
            st.st_mode = stat.S_IFREG | 0o666
            st.st_nlink = 1
            st_size = self.get_mongo_size(path)
            syslog.syslog(syslog.LOG_NOTICE, " * * getattr() size=%d" % st_size)
            st.st_size = st_size
            st_ctime = self.get_mongo_ctime(path)
            syslog.syslog(syslog.LOG_NOTICE, " * * getattr() st_ctime=%d" % st_ctime)
            st.st_ctime = st_ctime
            st.st_mtime = st_ctime
        elif ft == FIOC_NONE:
            syslog.syslog(syslog.LOG_NOTICE, " * getattr(): ENOENT")
            return errno.ENOENT
        else:
            syslog.syslog(syslog.LOG_NOTICE, " * getattr(): -ENOENT")
            return -errno.ENOENT
            #return 0
        return st

    def open(self, path, flags):
        syslog.syslog(syslog.LOG_NOTICE, "FiocFS.open()")
        if self.file_type(path) != FIOC_NONE:
            syslog.syslog(syslog.LOG_NOTICE, " * returning 0")
            return 0

        syslog.syslog(syslog.LOG_NOTICE, " * returning ENOENT")
        return -errno.ENOENT

    def mongo_do_read(self, path):
        syslog.syslog(syslog.LOG_NOTICE, "FiocFS.mongo_do_read()")
        filename = path[1:]
        syslog.syslog(syslog.LOG_NOTICE, " * mongo_do_read(): filename=%s" % filename)
        obj = self.mongo.search_db(filename)[0]
        content = obj['content']
        syslog.syslog(syslog.LOG_NOTICE, " * mongo_do_read(): first_line=%s" % content.split("\n")[0])
        del obj
        return content


    def do_read(self, path, size, offset):
        syslog.syslog(syslog.LOG_NOTICE, "FiocFS.do_read()")
        syslog.syslog(syslog.LOG_NOTICE, " * path=%s" % path)
        syslog.syslog(syslog.LOG_NOTICE, " * size=%d" % size)
        syslog.syslog(syslog.LOG_NOTICE, " * offset=%d" % offset)

        if self.is_mongo(path):
            sizeof = self.get_mongo_size(path)
            self.buf = self.mongo_do_read(path)

        if offset >= len(self.buf):
            return 0

        if size > (len(self.buf) - offset):
            size = len(self.buf) - offset

        return self.buf[offset:offset+size]

    def read(self, path, size, offset):
        syslog.syslog(syslog.LOG_NOTICE, "FiocFS.read()")
        syslog.syslog(syslog.LOG_NOTICE, " * path=%s" % path)
        syslog.syslog(syslog.LOG_NOTICE, " * size=%d" % size)
        syslog.syslog(syslog.LOG_NOTICE, " * offset=%d" % offset)

        if self.file_type(path) == FIOC_MONGO:
            syslog.syslog(syslog.LOG_NOTICE, " * read(): file_type(path) is FIOC_MONGO")
            pass
        elif self.file_type(path) != FIOC_FILE:
            syslog.syslog(syslog.LOG_NOTICE, " * * returns EINVAL")
            return -errno.EINVAL;

        return self.do_read(path, size, offset)

    def do_write(self, path, buf, offset):
        syslog.syslog(syslog.LOG_NOTICE, "FiocFS.do_write()")
        syslog.syslog(syslog.LOG_NOTICE, " * path=%s" % path)
        syslog.syslog(syslog.LOG_NOTICE, " * size=%d" % size)
        syslog.syslog(syslog.LOG_NOTICE, " * offset=%d" % offset)

        self.buf = self.buf[0:offset-1] + buf + self.buf[offset+len(buf)+1:len(self.buf)]
        return len(buf)

    def write(self, path, buf, offset):
        syslog.syslog(syslog.LOG_NOTICE, "FiocFS.write()")
        syslog.syslog(syslog.LOG_NOTICE, " * path=%s" % path)
        syslog.syslog(syslog.LOG_NOTICE, " * size=%d" % size)
        syslog.syslog(syslog.LOG_NOTICE, " * offset=%d" % offset)

        if self.file_type(path) != FIOC_FILE:
            return -errno.EINVAL;

        return self.do_write(path, buf, offset)

    def truncate(self, path, size):
        syslog.syslog(syslog.LOG_NOTICE, "FiocFS.truncate()")
        syslog.syslog(syslog.LOG_NOTICE, " * path=%s" % path)
        syslog.syslog(syslog.LOG_NOTICE, " * size=%d" % size)

        if self.file_type(path) != FIOC_FILE:
            return -error.EINVAL

        return self.resize(size)

    def readdir(self, path, offset):
        syslog.syslog(syslog.LOG_NOTICE, "FiocFS.readdir()")
        syslog.syslog(syslog.LOG_NOTICE, " * path=%s" % path)
        syslog.syslog(syslog.LOG_NOTICE, " * offset=%d" % offset)

        for r in  '.', '..', FIOC_NAME:
            syslog.syslog(syslog.LOG_NOTICE, " * fuse.Direntry(): %s" % r)
            yield fuse.Direntry(r)

        for r in self.mongo_files:
            syslog.syslog(syslog.LOG_NOTICE, " * fuse.Direntry(): %s" % r)
            yield fuse.Direntry(r)

    def ioctl(self, path, cmd, arg, flags):
        syslog.syslog(syslog.LOG_NOTICE, "FiocFS.ioctl()")
        syslog.syslog(syslog.LOG_NOTICE, " * path=%s" % path)
        syslog.syslog(syslog.LOG_NOTICE, " * cmd=%d" % cmd)
        syslog.syslog(syslog.LOG_NOTICE, " * arg=%s" % arg)
        syslog.syslog(syslog.LOG_NOTICE, " * flags=%d" % flags)

        if cmd == FIOC_GET_SIZE:
            data = struct.pack("L",len(self.buf))
            return data
        elif cmd == FIOC_SET_SIZE:
            (l,) = struct.unpack("L",arg);
            self.resize(l)
            return 0

        return -errno.EINVAL

    def access(self, *args, **kargs):
        syslog.syslog(syslog.LOG_NOTICE, "FiocFS.access()")

    def main(self, *a, **kw):
        syslog.syslog(syslog.LOG_NOTICE, "FiocFS.main()")

        self.file_class = XmpFile
        return Fuse.main(self, *a, **kw)


def main():
    syslog.syslog(syslog.LOG_NOTICE, "main()")
    usage="""
Userspace ioctl example

""" + Fuse.fusage
    server = FiocFS(version="%prog " + fuse.__version__,
                     usage=usage,
                     dash_s_do='setsingle')

    #mongo = MongoDB()
    #mongo.test_populate_db()
    #mongo.test(directory=sys.argv[1])

    server.parse(errex=1)
    server.main()

if __name__ == '__main__':
    syslog.openlog("fuse-mongodb")
    main()
    syslog.closelog()

