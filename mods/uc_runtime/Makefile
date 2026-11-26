# Builds the runtime against the engine fork's plugin API (its docs/PLUGINS.md).
# The runtime is the mod's one native library (docs/decisions.md#0013): src/runtime.c and
# src/ids.c compile into it, and src/ids.h and src/modules.h are generated from
# data/ids/registry.csv by tools/check_ids.py --write.
#
#   make                     uc_runtime.so next to mod.json
#   make FORK=/path/to/fork  against another checkout of MH4UltimateDC-fork
#   make test                the id layer on a fake host, with no game
#   make clean

FORK ?= ../../../MH4UltimateDC-fork
CC ?= cc
CFLAGS ?= -std=c99 -O2 -Wall -Wextra
TARGET := $(if $(filter Darwin,$(shell uname -s)),uc_runtime.dylib,uc_runtime.so)
SOURCES := src/runtime.c src/ids.c
HEADERS := src/runtime.h src/ids.h src/modules.h

all: $(TARGET)

$(TARGET): $(SOURCES) $(HEADERS)
	$(CC) $(CFLAGS) -fPIC -shared -I$(FORK)/include $(SOURCES) -o $@

# The moved id layer's behaviour, on a fake host: the hooks the runtime asks for, a registered
# id answered with its stand-in, and an MH4U id passed through (tests/test_runtime.c).
test: $(TARGET)
	$(CC) $(CFLAGS) -I$(FORK)/include -Isrc $(SOURCES) tests/test_runtime.c -o tests/test_runtime
	./tests/test_runtime

clean:
	rm -f uc_runtime.so uc_runtime.dylib uc_runtime.dll tests/test_runtime

.PHONY: all test clean
