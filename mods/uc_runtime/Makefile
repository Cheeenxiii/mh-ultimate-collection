# Builds the runtime against the engine fork's plugin API (its docs/PLUGINS.md).
# The runtime is the mod's one native library (docs/decisions.md#0013): src/runtime.c,
# src/ids.c and src/module.c compile into it with one file per ported monster from
# src/monsters/, plus the ported monsters' action families from src/monsters/<monster>/*.c.
# src/ids.h and src/modules.h are generated from data/ids/registry.csv by
# tools/check_ids.py --write, and each monster's family list (families.h) is generated from
# its family directory by tools/gen_families.py at build time.
#
#   make                     uc_runtime.so next to mod.json
#   make FORK=/path/to/fork  against another checkout of MH4UltimateDC-fork
#   make test                the id layer and the modules on a fake host, no game
#   make clean

FORK ?= ../../../MH4UltimateDC-fork
CC ?= cc
PYTHON ?= python3
CFLAGS ?= -std=c99 -O2 -Wall -Wextra
LDLIBS ?= -lm
TARGET := $(if $(filter Darwin,$(shell uname -s)),uc_runtime.dylib,uc_runtime.so)
MONSTER_SOURCES := $(wildcard src/monsters/*.c)
# The monsters whose actions are split into families: one .c per family under
# src/monsters/<key>/, discovered by tools/gen_families.py. The tag is the short C name the
# generated list and the family symbols carry (mhuc_3u_family_cat0, mhuc_gu_family_cat17).
FAMILY_KEYS := rathian-3u rathian-gu
FAMILY_TAG_rathian-3u := 3u
FAMILY_TAG_rathian-gu := gu
FAMILY_SOURCES := $(foreach k,$(FAMILY_KEYS),$(wildcard src/monsters/$(k)/*.c))
FAMILY_HEADERS := $(foreach k,$(FAMILY_KEYS),src/monsters/$(k)/families.h)
SOURCES := src/runtime.c src/ids.c src/module.c $(MONSTER_SOURCES) $(FAMILY_SOURCES)
HEADERS := src/runtime.h src/module.h src/ids.h src/modules.h $(FAMILY_HEADERS)
TESTS := tests/test_runtime tests/test_module tests/test_rathian_3u tests/test_family_discovery
# The action families' tests: one program per file under tests/<key>/, discovered from the
# directory like the module's family list. A slice writes tests/<key>/<family>.c and edits
# nothing here. The 3U module's programs keep their names (tests/family-cat0); a second
# module's carry its tag (tests/family-gu-cat17), so two modules may use the same family file
# name. FAMILY_TEST_INCLUDE is the directory holding the test key's host.h.
TEST_KEYS := $(FAMILY_KEYS)
FAMILY_TEST_PREFIX_rathian-3u :=
FAMILY_TEST_PREFIX_rathian-gu := gu-
FAMILY_TEST_INCLUDE_rathian-3u := tests/rathian-3u
FAMILY_TEST_INCLUDE_rathian-gu := tests/rathian-gu
FAMILY_TEST_DIRS := $(addprefix tests/,$(TEST_KEYS))
FAMILY_TESTS := $(foreach k,$(TEST_KEYS),\
	$(patsubst tests/$(k)/%.c,tests/family-$(FAMILY_TEST_PREFIX_$(k))%,\
	$(wildcard tests/$(k)/*.c)))

all: $(TARGET)

# Each family list, discovered from its directory: adding src/monsters/<key>/<family>.c is all
# a slice does. FORCE reruns the generator every make, so a removed file drops out too; the
# generator keeps the header's mtime when the set is unchanged, so the plugin isn't rebuilt.
define FAMILY_HEADER_RULE
src/monsters/$(1)/families.h: $(wildcard src/monsters/$(1)/*.c) ../../tools/gen_families.py FORCE
	$(PYTHON) ../../tools/gen_families.py --dir src/monsters/$(1) --tag $(FAMILY_TAG_$(1)) --out $$@
endef
$(foreach k,$(FAMILY_KEYS),$(eval $(call FAMILY_HEADER_RULE,$(k))))

FORCE:

$(TARGET): $(SOURCES) $(HEADERS)
	$(CC) $(CFLAGS) -fPIC -shared -I$(FORK)/include -Isrc $(SOURCES) -o $@ $(LDLIBS)

# The id layer's and the modules' behaviour, on a fake host: the hooks the runtime asks for, a
# registered id answered with its stand-in, an MH4U id passed through, the factory association,
# the action routing, and the translated actions' call sequences (tests/test_runtime.c,
# tests/test_module.c for the GU module's shell, tests/test_rathian_3u.c for the 3U module's
# shell and one program per action family, all on tests/fake_host.c), plus the family-list
# discovery (tests/test_family_discovery.c, built against a generated probe) and the
# test-list discovery (test-family-discovery, built against a probe family test).
test: $(TESTS)
	./tests/test_runtime
	./tests/test_module
	./tests/test_rathian_3u
	$(MAKE) --no-print-directory test-family-tests
	$(MAKE) --no-print-directory test-family-discovery

# The family tests the wildcards found: build and run each. A slice adds
# tests/<key>/<family>.c and this finds it. An empty list is an error, so a discovery target
# can't pass by finding nothing.
test-family-tests: $(FAMILY_TESTS)
	@test -n "$(FAMILY_TESTS)" || { echo "no family tests in $(FAMILY_TEST_DIRS)" >&2; exit 1; }
	@set -e; for t in $(FAMILY_TESTS); do echo "$$t"; "$$t"; done

tests/test_runtime: $(SOURCES) $(HEADERS) tests/fake_host.c tests/fake_host.h tests/test_runtime.c
	$(CC) $(CFLAGS) -I$(FORK)/include -Isrc tests/fake_host.c tests/test_runtime.c $(SOURCES) \
		-o $@ $(LDLIBS)

tests/test_module: $(SOURCES) $(HEADERS) tests/fake_host.c tests/fake_host.h tests/test_module.c
	$(CC) $(CFLAGS) -I$(FORK)/include -Isrc tests/fake_host.c tests/test_module.c $(SOURCES) \
		-o $@ $(LDLIBS)

tests/test_rathian_3u: $(SOURCES) $(HEADERS) tests/fake_host.c tests/fake_host.h \
		tests/rathian-3u/host.h tests/test_rathian_3u.c
	$(CC) $(CFLAGS) -I$(FORK)/include -Isrc tests/fake_host.c tests/test_rathian_3u.c $(SOURCES) \
		-o $@ $(LDLIBS)

# One family test program per file in each family test directory. The static pattern rule maps
# tests/<key>/<family>.c to tests/family-<tag><family>. The probe (test-family-discovery) gives
# TEST_KEYS one throwaway key, so this same wildcard and rule build it.
define FAMILY_TEST_RULE
$(patsubst tests/$(1)/%.c,tests/family-$(FAMILY_TEST_PREFIX_$(1))%,\
$(wildcard tests/$(1)/*.c)): tests/family-$(FAMILY_TEST_PREFIX_$(1))%: tests/$(1)/%.c \
		$(SOURCES) $(HEADERS) tests/fake_host.c tests/fake_host.h \
		$(FAMILY_TEST_INCLUDE_$(1))/host.h
	$(CC) $(CFLAGS) -I$(FORK)/include -Isrc -I$(FAMILY_TEST_INCLUDE_$(1)) tests/fake_host.c \
		$$< $(SOURCES) -o $$@ $(LDLIBS)
endef
$(foreach k,$(TEST_KEYS),\
	$(if $(wildcard tests/$(k)/*.c),$(eval $(call FAMILY_TEST_RULE,$(k)))))

# The discovery test: a family file the module doesn't ship is put in a directory of its own,
# the generator writes its list, and the test calls the entry the list discovered.
tests/family-probe/families.h: ../../tools/gen_families.py tests/fixtures/rathian-3u/probe.c
	rm -rf tests/family-probe
	mkdir -p tests/family-probe
	cp tests/fixtures/rathian-3u/probe.c tests/family-probe/probe.c
	$(PYTHON) ../../tools/gen_families.py --dir tests/family-probe --out $@

tests/test_family_discovery: tests/family-probe/families.h tests/test_family_discovery.c \
		src/monsters/rathian-3u/family.h src/module.h
	$(CC) $(CFLAGS) -I$(FORK)/include -Itests/family-probe -Isrc/monsters/rathian-3u -Isrc \
		tests/test_family_discovery.c tests/family-probe/probe.c -o $@

# The test list is discovered, not written: this target puts a probe family test in a directory
# of its own and makes the wildcard's list build and run it, with no other edit. A slice does
# the same by writing tests/<key>/<family>.c; if the wildcard missed it, test-family-tests
# fails on the probe (or on an empty real list).
test-family-discovery: tests/fixtures/rathian-3u/probe_test.c
	rm -rf tests/probe-tests tests/family-probe-*
	mkdir -p tests/probe-tests
	cp tests/fixtures/rathian-3u/probe_test.c tests/probe-tests/probe-test.c
	$(MAKE) --no-print-directory \
		TEST_KEYS="$(TEST_KEYS) probe-tests" \
		FAMILY_TEST_PREFIX_probe-tests=probe- \
		FAMILY_TEST_INCLUDE_probe-tests=tests/rathian-3u \
		test-family-tests
	rm -rf tests/probe-tests tests/family-probe-*

clean:
	rm -f $(TARGET) $(TESTS) $(FAMILY_TESTS) $(FAMILY_HEADERS)
	rm -rf tests/family-probe tests/probe-tests tests/family-probe-*

.PHONY: all test clean test-family-tests test-family-discovery FORCE
