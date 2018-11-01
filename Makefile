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
INCLUDES = $(INCLIB) -g
#---------------------------------------------------------
# Explicit targets
#---------------------------------------------------------

all: $(BINS)

fuse-mongodb: fuse-mongodb.o
	$(CC) -o $@ $< $(LDFLAGS)

mongo-example: mongo-example.o
	$(CC) -o $@ $< $(LDFLAGS)

%.o: %.c
	@$(CC) $(INCLUDES) -c $< -o $@

.PHONY: clean
clean:
	-rm -f *.o *~ $(PGM) core *.core
