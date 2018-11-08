#!/usr/bin/python3

from pymongo import MongoClient
import gridfs
import os
import syslog
import random
import datetime
import mipsum

def alert(message):
    print(message)
    syslog.syslog(syslog.LOG_NOTICE, message)

class MongoData:
    _server_url = 'mongodb://100.109.0.1:27017'
    now = datetime.datetime.utcnow()
    uid = os.getuid()
    gid = os.getgid()
    permission = 0o755

    def __init__(self):
        alert( "MongoDB.__init__()")
        client = MongoClient(self._server_url)
        db = client.testdb
        self.xfs = db.xfs
        #self.fs = gridfs.GridFS(db)
        #self.fsb = gridfs.GridFSBucket(db)
        alert( "MongoDB.__init__() ends")

    def list_files(self, directory=None):
        alert( "MongoDB.list_files()")
        filenames = []
        for content in self.xfs.find():
            filepath = content['filename']
            #if directory is not None:
            #    filepath = re.sub("/mnt/mongodb", directory, filepath)
            filenames.append(filepath)
        return filenames

    def get_extension(self):
        patterns = [ "doc", "txt", "info", "man", "text", "tex", "latex" ]
        size = len(patterns)
        return patterns[random.randint(0, size - 1)]

    def insert_file(self, filename, content):
        alert( "MongoDB.insert_file()")
        alert( " * filename=%s" % filename)
        json = {
            "filename" : filename,
            "content" : content,
            "date" : self.now,
            "gid" : self.gid,
            "uid" : self.uid,
            "permission" : self.permission
            }
        self.xfs.insert_one(json)

    def test_insert_db(self):
        alert( "MongoDB.test_insert_db()")
        filename = "myfile-%d" % random.randint(0,99999)
        extension = self.get_extension()
        filename += "." + extension
        m = mipsum.MussumLorum()
        text = "\n\n".join(m.get_paragraph())
        json = {
            "filename" : filename,
            "content" : text,
            "date" : self.now,
            "gid" : self.gid,
            "uid" : self.uid,
            "permission" : self.permission
            }
        result = self.xfs.insert_one(json)
        alert( " test_insert_db(): post_id=%s" % result.inserted_id)
        return filename

    def search_db(self, filename):
        alert( "MongoDB.search_db()")
        alert( " * filename=%s" % filename)
        return self.xfs.find({ "filename" : filename })

    def test_delete_db(self, filename):
        alert( "MongoDB.test_delete_db()")
        alert( " * filename=%s" % filename)
        for entry in self.xfs.find({ "filename" : filename }):
            self.xfs.delete_one(entry)

    def test_populate_db(self, counter=None):
        alert( "MongoDB.test_populate_db()")
        if counter is None:
            counter = 10
        alert( " * counter=%d" % counter)
        while counter > 0:
            self.test_insert_db()
            counter -= 1

    def test(self, directory=None):
        alert( "MongoDB.test()")
        alert( "MongoDB.__init__()")
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



if __name__ == '__main__':
    client = MongoData()
    client.test_populate_db()
