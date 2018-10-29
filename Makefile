PGM = fuse-mongodb

OBJS =  fuse-mongodb.o

INCLIB = -I../libfuse/include
INCLIB += $(shell pkg-config --cflags libbson-1.0)

#---------------------------------------------------------
# Compiler & linker flags
#---------------------------------------------------------

CXXFLAGS = -Wall -Werror -g -std=c++14 -D_FILE_OFFSET_BITS=64
LDFLAGS = -lfuse3 -g
LDFLAGS += $(shell pkg-config --libs libmongoc-1.0)
LDFLAGS += $(shell pkg-config --libs libbson-1.0)
LDFLAGS += -L../libfuse/build/lib
INCLUDES = $(INCLIB)
#---------------------------------------------------------
# Explicit targets
#---------------------------------------------------------

all: $(PGM)

$(PGM): $(OBJS) $(PGM).c
	$(CC) -o $@ $(OBJS) $(LDFLAGS)

$(OBJS): %.c:
	$(CC) $(INCLUDES) -c $(PGM).c $< -o $@

.PHONY: clean
clean:
	-rm -f *.o *~ $(PGM) core *.core
