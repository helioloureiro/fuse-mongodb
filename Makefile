BINS = fuse-mongodb
BINS += mongo-example

OBJS = fuse-mongodb.o
OBJS += mongo-example.o

SRCS =  fuse-mongodb.c
SRCS += mongo-example.c

INCLIB += $(shell pkg-config --cflags --libs libbson-1.0)
INCLIB += $(shell pkg-config --cflags --libs libmongoc-1.0)
INCLIB += $(shell pkg-config --cflags fuse)

#---------------------------------------------------------
# Compiler & linker flags
#---------------------------------------------------------

LDFLAGS = -g
LDFLAGS += $(shell pkg-config --libs --cflags libmongoc-1.0)
LDFLAGS += $(shell pkg-config --libs --cflags libbson-1.0)
LDFLAGS += $(shell pkg-config --libs fuse)
INCLUDES = $(INCLIB)
#---------------------------------------------------------
# Explicit targets
#---------------------------------------------------------

all: $(BINS)

$(BINS): $(OBJS)
	$(CC) -o $@ $< $(LDFLAGS)

$(OBJS): $(SRCS)
	$(CC) $(INCLUDES) -c $< -o $@

.PHONY: clean
clean:
	-rm -f *.o *~ $(PGM) core *.core
