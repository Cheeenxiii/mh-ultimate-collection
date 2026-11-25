# Builds the ported-monster action-id plugin against the engine fork's plugin API
# (its docs/PLUGINS.md). mod.json names it and the game function it wraps.
# src/actions.h is generated from the per-id table by reference/monster_handlers.py table.
#
#   make                     monster_actions.so next to mod.json
#   make FORK=/path/to/fork  against another checkout of MH4UltimateDC-fork
#   make clean

FORK ?= ../../../MH4UltimateDC-fork
CC ?= cc
CFLAGS ?= -std=c99 -O2 -Wall -Wextra
TARGET := $(if $(filter Darwin,$(shell uname -s)),monster_actions.dylib,monster_actions.so)

all: $(TARGET)

$(TARGET): src/monster_actions.c src/actions.h
	$(CC) $(CFLAGS) -fPIC -shared -I$(FORK)/include $< -o $@

clean:
	rm -f monster_actions.so monster_actions.dylib monster_actions.dll

.PHONY: all clean
