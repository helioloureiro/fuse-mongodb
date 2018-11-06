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


try:
    import _find_fuse_parts
except ImportError:
    pass
import fuse
from fuse import Fuse

if not hasattr(fuse, '__version__'):
    raise RuntimeError("your fuse-py doesn't know of fuse.__version__, probably it's too old.")

fuse.fuse_python_api = (0, 2)

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

    def list_files(self, directory=None):
        filenames = []
        for content in self.xfs.find():
            filepath = content['filename']
            if directory is not None:
                filepath = re.sub("/mnt/mongodb", directory, filepath)
            filenames.append(filepath)
        return filenames

    def insert_file(self, filename, content):
        json = {
            "filename" : filename,
            "content" : content,
            "date" : datetime.datetime.utcnow()
            }
        self.xfs.insert_one(json)

    def test_insert_db(self):
        filename = "/mnt/mongodb/myfile-%d.txt" % random.randint(0,99999)
        post = {"filename": filename,
                "content" : "whatever",
                "date": datetime.datetime.utcnow()}

        post_id = self.xfs.insert_one(post)
        print("post_id:", post_id)
        return filename

    def search_db(self, filename):
        return self.xfs.find({ "filename" : filename })

    def test_delete_db(self, filename):
        for entry in self.xfs.find({ "filename" : filename }):
            self.xfs.delete_one(entry)

    def test(self, directory=None):
        syslog.syslog(syslog.LOG_NOTICE, "MongoDB.__init__()")
        # insert
        print("inserting file...")
        filename = self.test_insert_db()
        print(" * file=%s inserted" % filename)\

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


class MyStat(fuse.Stat):
    def __init__(self):
        self.st_mode = 0
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 0
        self.st_uid = 0
        self.st_gid = 0
        self.st_size = 0
        self.st_atime = 0
        self.st_mtime = 0
        self.st_ctime = 0


class FiocFS(Fuse):

    def __init__(self, *args, **kw):
        syslog.syslog(syslog.LOG_NOTICE, "FiocFS.__init__()")
        Fuse.__init__(self, *args, **kw)
        self.buf =  ""

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
        if not type(path) == str:
            return FIOC_NONE
        if path == "/":
            return FIOC_ROOT
        elif path == "/" + FIOC_NAME:
            return FIOC_FILE
        else:
            return FIOC_NONE

    def getattr(self, path):
        syslog.syslog(syslog.LOG_NOTICE, "FiocFS.getattr()")
        st = MyStat()
        ft = self.file_type(path)
        if ft == FIOC_ROOT:
            st.st_mode = stat.S_IFDIR | 0o755
            st.st_nlink = 2
        elif ft == FIOC_FILE:
            st.st_mode = stat.S_IFREG | 0o666
            st.st_nlink = 1
            st.st_size = len(self.buf)
        else:
            return -errno.ENOENT
        return st

    def open(self, path, flags):
        syslog.syslog(syslog.LOG_NOTICE, "FiocFS.open()")
        if self.file_type(path) != FIOC_NONE:
            return 0

        return -errno.ENOENT

    def do_read(self, path, size, offset):
        syslog.syslog(syslog.LOG_NOTICE, "FiocFS.do_read()")

        if offset >= len(self.buf):
            return 0

        if size > (len(self.buf) - offset):
            size = len(self.buf) - offset

        return self.buf[offset:offset+size]

    def read(self, path, size, offset):
        syslog.syslog(syslog.LOG_NOTICE, "FiocFS.read()")
        if self.file_type(path) != FIOC_FILE:
            return -errno.EINVAL;

        return self.do_read(path, size, offset)

    def do_write(self, path, buf, offset):
        syslog.syslog(syslog.LOG_NOTICE, "FiocFS.do_write()")
        self.buf = self.buf[0:offset-1] + buf + self.buf[offset+len(buf)+1:len(self.buf)]
        return len(buf)

    def write(self, path, buf, offset):
        syslog.syslog(syslog.LOG_NOTICE, "FiocFS.write()")
        if self.file_type(path) != FIOC_FILE:
            return -errno.EINVAL;

        return self.do_write(path, buf, offset)

    def truncate(self, path, size):
        syslog.syslog(syslog.LOG_NOTICE, "FiocFS.truncate()")
        if self.file_type(path) != FIOC_FILE:
            return -error.EINVAL

        return self.resize(size)

    def readdir(self, path, offset):
        syslog.syslog(syslog.LOG_NOTICE, "readdir()")
        for r in  '.', '..', FIOC_NAME:
            yield fuse.Direntry(r)

    def ioctl(self, path, cmd, arg, flags):
        syslog.syslog(syslog.LOG_NOTICE, "FiocFS.ioctl()")
        if cmd == FIOC_GET_SIZE:
            data = struct.pack("L",len(self.buf))
            return data
        elif cmd == FIOC_SET_SIZE:
            (l,) = struct.unpack("L",arg);
            self.resize(l)
            return 0

        return -errno.EINVAL

def main():
    syslog.syslog(syslog.LOG_NOTICE, "main()")
    usage="""
Userspace ioctl example

""" + Fuse.fusage
    server = FiocFS(version="%prog " + fuse.__version__,
                     usage=usage,
                     dash_s_do='setsingle')

    mongo = MongoDB()
    mongo.test(directory=sys.argv[1])

    server.parse(errex=1)
    server.main()

if __name__ == '__main__':
    syslog.openlog("fuse-mongodb")
    main()
    syslog.closelog()

