BINS = fuse-mongodb mongo-example

OBJS = fuse-mongodb.o mongo-example.o
SRCS = fuse-mongodb.c mongo-example.c

INCLIB += $(shell pkg-config --cflags libbson-1.0)
INCLIB += $(shell pkg-config --cflags libmongoc-1.0)
INCLIB += $(shell pkg-config --cflags fuse)

#---------------------------------------------------------
# Compiler & linker flags
#---------------------------------------------------------

CXXFLAGS = -Wall -Werror -g -std=c++14 -D_FILE_OFFSET_BITS=64
LDFLAGS = -g
LDFLAGS += $(shell pkg-config --libs libmongoc-1.0)
LDFLAGS += $(shell pkg-config --libs libbson-1.0)
LDFLAGS += $(shell pkg-config --libs fuse)
INCLUDES = $(INCLIB)
#---------------------------------------------------------
# Explicit targets
#---------------------------------------------------------

all: $(BINS)

$(BINS): $(OBJS)
	$(CC) -o $@ $(LDFLAGS) $<

$(OBJS): $(SRCS)
	$(CC) $(INCLUDES) -c $< -o $@

.PHONY: clean
clean:
	-rm -f *.o *~ $(PGM) core *.core
