/*
 * FUSE-MONGODB
 *
 * A modification over hello_ll from libfuse/examples.
 * Available on /usr/share/doc/libfuse-dev/examples/hello_ll.c
 * on Ubuntu 16.04 at package libfuse-dev.
 *
 * FUSE: Filesystem in Userspace
 * Copyright (C) 2001-2007  Miklos Szeredi <miklos@szeredi.hu>
 *
 * This program can be distributed under the terms of the GNU GPL.
 * See the file COPYING.
 *
 * gcc -Wall hello_ll.c `pkg-config fuse --cflags --libs` -o hello_ll
*/

#define FUSE_USE_VERSION 26

#include <fuse_lowlevel.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <assert.h>
#include <syslog.h>
#include <time.h>

/* mongoc */
#include <bson.h>
#include <mongoc.h>


static const char *hello_str = "Hello World!\n";
static const char *hello_name = "hello";
static const char *mongodb_settings = "mongodb://100.109.0.1:27017/testdb";
static mongoc_client_t *mongo_client;
static mongoc_collection_t *mongo_collection;
static mongoc_cursor_t *mongo_cursor;
static bson_error_t bson_error;
static bson_oid_t bson_oid;
static bson_t *bson_doc;


static int hello_stat(fuse_ino_t ino, struct stat *stbuf){
    syslog(LOG_NOTICE, "hello_stat() called");
    syslog(LOG_NOTICE, " * hello_stat() ino=%d", (int) ino);
	stbuf->st_ino = ino;
    stbuf->st_uid = getuid();
    stbuf->st_gid = getgid();
    stbuf->st_atime = stbuf->st_mtime = time(NULL);
    syslog(LOG_NOTICE, " * hello_stat() st_dev=%d", (int) stbuf->st_dev);

	switch (ino) {
	case 1:
		stbuf->st_mode = S_IFDIR | 0755;
		stbuf->st_nlink = 2;
		break;

	case 2:
		stbuf->st_mode = S_IFREG | 0644;
		stbuf->st_nlink = 1;
		stbuf->st_size = strlen(hello_str);
		break;

	default:
		return -1;
	}
	return 0;
}

static void hello_ll_getattr(fuse_req_t req, fuse_ino_t ino,
			     struct fuse_file_info *fi){
    syslog(LOG_NOTICE, "hello_ll_getattr() called");
	struct stat stbuf;

	(void) fi;

	memset(&stbuf, 0, sizeof(stbuf));
	if (hello_stat(ino, &stbuf) == -1)
		fuse_reply_err(req, ENOENT);
	else
		fuse_reply_attr(req, &stbuf, 1.0);
}

static void hello_ll_lookup(fuse_req_t req, fuse_ino_t parent, const char *name){
    syslog(LOG_NOTICE, "hello_lookup() called");
	struct fuse_entry_param e;

	if (parent != 1 || strcmp(name, hello_name) != 0)
		fuse_reply_err(req, ENOENT);
	else {
		memset(&e, 0, sizeof(e));
		e.ino = 2;
		e.attr_timeout = 1.0;
		e.entry_timeout = 1.0;
		hello_stat(e.ino, &e.attr);

		fuse_reply_entry(req, &e);
	}
}

struct dirbuf {
	char *p;
	size_t size;
};

static void dirbuf_add(fuse_req_t req, struct dirbuf *b, const char *name,
		       fuse_ino_t ino){
    syslog(LOG_NOTICE, "dirbuf_add() called for %s", name);
    syslog(LOG_NOTICE, " * dirbuf_add() ino=%d", (int) ino);
	struct stat stbuf;
	size_t oldsize = b->size;
	b->size += fuse_add_direntry(req, NULL, 0, name, NULL, 0);
	b->p = (char *) realloc(b->p, b->size);
    syslog(LOG_NOTICE, " * dirbuf_add() b->p=%p", b->p);
	memset(&stbuf, 0, sizeof(stbuf));
	stbuf.st_ino = ino;
	fuse_add_direntry(req, b->p + oldsize, b->size - oldsize, name, &stbuf,
			  b->size);
}

#define min(x, y) ((x) < (y) ? (x) : (y))

static int reply_buf_limited(fuse_req_t req, const char *buf, size_t bufsize,
			     off_t off, size_t maxsize){
    syslog(LOG_NOTICE, "reply_buf_limited() called");
	if (off < bufsize)
		return fuse_reply_buf(req, buf + off,
				      min(bufsize - off, maxsize));
	else
		return fuse_reply_buf(req, NULL, 0);
}

static void hello_ll_readdir(fuse_req_t req, fuse_ino_t ino, size_t size,
			     off_t off, struct fuse_file_info *fi){
    syslog(LOG_NOTICE, "hello_ll_readdir() called");
	(void) fi;

    syslog(LOG_NOTICE, " * hello_ll_readdir() ino=%d", (int) ino);
	if (ino != 1)
		fuse_reply_err(req, ENOTDIR);
	else {
		struct dirbuf b;
        char *str;
        bson_t *query;

		memset(&b, 0, sizeof(b));
		dirbuf_add(req, &b, ".", 1);
		dirbuf_add(req, &b, "..", 1);

        query = bson_new();
        BSON_APPEND_UTF8(query, "hello", "world");

        mongo_cursor = mongoc_collection_find (mongo_collection, MONGOC_QUERY_NONE, 0, 0, 0, query, NULL, NULL);

        while (mongoc_cursor_next (mongo_cursor, &bson_doc)) {
            str = bson_as_json(bson_doc, NULL);
            syslog(LOG_NOTICE, "str=%s", str);
            //dirbuf_add(req, &b, str, 2);
            bson_free(str);
        }

		dirbuf_add(req, &b, hello_name, 2);
		reply_buf_limited(req, b.p, b.size, off, size);
		free(b.p);
	}
}

static void hello_ll_open(fuse_req_t req, fuse_ino_t ino,
			  struct fuse_file_info *fi){
    syslog(LOG_NOTICE, "hello_ll_open() called");
	if (ino != 2)
		fuse_reply_err(req, EISDIR);
	else if ((fi->flags & 3) != O_RDONLY)
		fuse_reply_err(req, EACCES);
	else
		fuse_reply_open(req, fi);
}

static void hello_ll_read(fuse_req_t req, fuse_ino_t ino, size_t size,
			  off_t off, struct fuse_file_info *fi){
    syslog(LOG_NOTICE, "hello_ll_read() called");
	(void) fi;

	assert(ino == 2);
	reply_buf_limited(req, hello_str, strlen(hello_str), off, size);
}

static void mongodb_init() {
    syslog(LOG_NOTICE, "mongodb_init() called");


    syslog(LOG_NOTICE, " * mongoc_init() called");
    mongoc_init();

    syslog(LOG_NOTICE, " * connection into mongo collection via client");
    mongo_client = mongoc_client_new (mongodb_settings);
    mongo_collection = mongoc_client_get_collection (mongo_client, "testdb", "testdb");

    syslog(LOG_NOTICE, " * creating new BSON doc");
    bson_doc = bson_new ();
    bson_oid_init(&bson_oid, NULL);
    syslog(LOG_NOTICE, " * BSON oid=%p", &bson_oid);
    BSON_APPEND_OID(bson_doc, "_id", &bson_oid);

    char *filename = "/mnt/mongodb/myfile";
    char *random;
    sprintf(random, "%d", rand());
    strcat(filename, random);
    syslog(LOG_NOTICE, " * filename=%s", filename);

    BSON_APPEND_UTF8(bson_doc, "hello", "world");

    syslog(LOG_NOTICE, " * inserting BSON doc into mongo collection");
    if (!mongoc_collection_insert(mongo_collection, MONGOC_INSERT_NONE, bson_doc, NULL, &bson_error)) {
        printf ("%s\n", bson_error.message);
    }

}

static void mongo_session_destroy() {
    syslog(LOG_NOTICE, "mongo_session_destroy() called");

    syslog(LOG_NOTICE, " * mongo and BSON destroying");
    bson_destroy (bson_doc);
    mongoc_collection_destroy (mongo_collection);
    mongoc_client_destroy (mongo_client);
}

static struct fuse_lowlevel_ops hello_ll_oper = {
    .init       = mongodb_init,
	.lookup		= hello_ll_lookup,
	.getattr	= hello_ll_getattr,
	.readdir	= hello_ll_readdir,
	.open		= hello_ll_open,
	.read		= hello_ll_read,
};

int main(int argc, char *argv[]){
    syslog(LOG_NOTICE, " ### main() called ###");
	struct fuse_args args = FUSE_ARGS_INIT(argc, argv);
	struct fuse_chan *ch;
	char *mountpoint;
	int err = -1;

	if (fuse_parse_cmdline(&args, &mountpoint, NULL, NULL) != -1 &&
	    (ch = fuse_mount(mountpoint, &args)) != NULL) {
		struct fuse_session *se;

		se = fuse_lowlevel_new(&args, &hello_ll_oper,
				       sizeof(hello_ll_oper), NULL);
		if (se != NULL) {
			if (fuse_set_signal_handlers(se) != -1) {
				fuse_session_add_chan(se, ch);
				err = fuse_session_loop(se);
				fuse_remove_signal_handlers(se);
				fuse_session_remove_chan(ch);
			}
			mongo_session_destroy();
			fuse_session_destroy(se);
		}
		fuse_unmount(mountpoint, ch);
	}
	fuse_opt_free_args(&args);
    syslog(LOG_NOTICE, " fuse exiting...  (error=%d)", err);
	return err ? 1 : 0;
}
