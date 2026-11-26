# Builds the runtime against the engine fork's plugin API (its docs/PLUGINS.md).
# The runtime is the mod's one native library (docs/decisions.md#0013): src/runtime.c,
# src/ids.c and src/module.c compile into it with one file per ported monster from
# src/monsters/, and src/ids.h and src/modules.h are generated from data/ids/registry.csv by
# tools/check_ids.py --write.
#
#   make                     uc_runtime.so next to mod.json
#   make FORK=/path/to/fork  against another checkout of MH4UltimateDC-fork
#   make test                the id layer and the GU Rathian module on a fake host, no game
#   make clean

FORK ?= ../../../MH4UltimateDC-fork
CC ?= cc
CFLAGS ?= -std=c99 -O2 -Wall -Wextra
LDLIBS ?= -lm
TARGET := $(if $(filter Darwin,$(shell uname -s)),uc_runtime.dylib,uc_runtime.so)
SOURCES := src/runtime.c src/ids.c src/module.c $(wildcard src/monsters/*.c)
HEADERS := src/runtime.h src/module.h src/ids.h src/modules.h
TESTS := tests/test_runtime tests/test_module

all: $(TARGET)

$(TARGET): $(SOURCES) $(HEADERS)
	$(CC) $(CFLAGS) -fPIC -shared -I$(FORK)/include $(SOURCES) -o $@ $(LDLIBS)

# The id layer's and the modules' behaviour, on a fake host: the hooks the runtime asks for, a
# registered id answered with its stand-in, an MH4U id passed through, the factory association,
# the action routing, and the translated actions' call sequences (tests/test_runtime.c,
# tests/test_module.c, both on tests/fake_host.c).
test: $(TESTS)
	./tests/test_runtime
	./tests/test_module

tests/test_runtime: $(SOURCES) $(HEADERS) tests/fake_host.c tests/fake_host.h tests/test_runtime.c
	$(CC) $(CFLAGS) -I$(FORK)/include -Isrc tests/fake_host.c tests/test_runtime.c $(SOURCES) \
		-o $@ $(LDLIBS)

tests/test_module: $(SOURCES) $(HEADERS) tests/fake_host.c tests/fake_host.h tests/test_module.c
	$(CC) $(CFLAGS) -I$(FORK)/include -Isrc tests/fake_host.c tests/test_module.c $(SOURCES) \
		-o $@ $(LDLIBS)

clean:
	rm -f uc_runtime.so uc_runtime.dylib uc_runtime.dll $(TESTS)

.PHONY: all test clean
