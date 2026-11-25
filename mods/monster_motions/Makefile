# Builds the ported-monster motion-translation plugin against the engine fork's plugin API
# (its docs/PLUGINS.md). The plugin is the mod's native library; mod.json names it and the game
# function it wraps.
# src/motions.h is generated from R1's comparison by reference/monster_motions.py table and
# checked by tools/check_motion_tables.py.
#
#   make                     monster_motions.so next to mod.json
#   make FORK=/path/to/fork  against another checkout of MH4UltimateDC-fork
#   make clean

FORK ?= ../../../MH4UltimateDC-fork
CC ?= cc
CFLAGS ?= -std=c99 -O2 -Wall -Wextra
TARGET := $(if $(filter Darwin,$(shell uname -s)),monster_motions.dylib,monster_motions.so)

all: $(TARGET)

$(TARGET): src/monster_motions.c src/motions.h
	$(CC) $(CFLAGS) -fPIC -shared -I$(FORK)/include $< -o $@

clean:
	rm -f monster_motions.so monster_motions.dylib monster_motions.dll

.PHONY: all clean
