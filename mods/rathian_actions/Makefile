# Builds the translated-action plugin against the engine fork's plugin API (its docs/PLUGINS.md).
# The plugin is the mod's native library; mod.json names it and the game function it wraps.
#
#   make                     rathian_actions.so next to mod.json
#   make FORK=/path/to/fork  against another checkout of MH4UltimateDC-fork
#   make clean

FORK ?= ../../../MH4UltimateDC-fork
CC ?= cc
CFLAGS ?= -std=c99 -O2 -Wall -Wextra
TARGET := $(if $(filter Darwin,$(shell uname -s)),rathian_actions.dylib,rathian_actions.so)

all: $(TARGET)

$(TARGET): src/rathian_actions.c
	$(CC) $(CFLAGS) -fPIC -shared -I$(FORK)/include $< -o $@

# The translated actions' call sequences, with a fake host and no game (test/test_plugin.c).
test: $(TARGET)
	$(CC) $(CFLAGS) -I$(FORK)/include test/test_plugin.c -o test/test_plugin
	./test/test_plugin

clean:
	rm -f rathian_actions.so rathian_actions.dylib rathian_actions.dll test/test_plugin

.PHONY: all test clean
