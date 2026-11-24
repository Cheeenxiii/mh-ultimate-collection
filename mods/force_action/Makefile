# Builds the forced-action plugin against the engine fork's plugin API (its docs/PLUGINS.md).
# The plugin is the mod's native library; mod.json names it and the game function it wraps.
#
#   make                     force_action.so next to mod.json
#   make FORK=/path/to/fork  against another checkout of MH4UltimateDC-fork
#   make clean

FORK ?= ../../../MH4UltimateDC-fork
CC ?= cc
CFLAGS ?= -std=c99 -O2 -Wall -Wextra
TARGET := $(if $(filter Darwin,$(shell uname -s)),force_action.dylib,force_action.so)

all: $(TARGET)

$(TARGET): src/force_action.c
	$(CC) $(CFLAGS) -fPIC -shared -I$(FORK)/include $< -o $@

clean:
	rm -f force_action.so force_action.dylib force_action.dll

.PHONY: all clean
