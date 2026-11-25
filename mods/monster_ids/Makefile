# Builds the ported-monster-id plugin against the engine fork's plugin API (its docs/PLUGINS.md).
# The plugin is the mod's native library; mod.json names it and the game functions it wraps.
# src/ids.h is generated from data/ids/registry.csv by tools/check_ids.py --write.
#
#   make                     monster_ids.so next to mod.json
#   make FORK=/path/to/fork  against another checkout of MH4UltimateDC-fork
#   make clean

FORK ?= ../../../MH4UltimateDC-fork
CC ?= cc
CFLAGS ?= -std=c99 -O2 -Wall -Wextra
TARGET := $(if $(filter Darwin,$(shell uname -s)),monster_ids.dylib,monster_ids.so)

all: $(TARGET)

$(TARGET): src/monster_ids.c src/ids.h
	$(CC) $(CFLAGS) -fPIC -shared -I$(FORK)/include $< -o $@

clean:
	rm -f monster_ids.so monster_ids.dylib monster_ids.dll

.PHONY: all clean
