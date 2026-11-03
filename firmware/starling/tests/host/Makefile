# SPDX-License-Identifier: Apache-2.0
# Host tests. PR #6 firmware/lora is fetched into .deps/ (gitignored) for
# gossip_hwm; other suites use pending_opencollar freshness shim only.
#
#   make -C firmware/starling/tests/host
#   PROTO_REF=origin/cursor/proto-fence-gossip-c865 make deps

CC ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -Werror -O1 -g
CFLAGS += -ffp-contract=off -D_POSIX_C_SOURCE=200809L

STARLING = ../..
FW = ../../..
REPO = $(FW)/..
SRC = $(FW)/src
CORE = $(FW)/core
MONO = $(FW)/third_party/monocypher
HOST_RAM = $(FW)/tests/host
DEPS = .deps
PROTO_REF ?= origin/cursor/proto-fence-gossip-c865
LORA = $(DEPS)/firmware/lora
SIM = $(DEPS)/firmware/sim
PENDING_INC = $(STARLING)/pending_opencollar

BASE_INC = -I$(STARLING)/src -I$(CORE) -I$(SRC) -I$(MONO) -I$(HOST_RAM)
CFLAGS += $(BASE_INC) -I$(PENDING_INC)

TESTS = geofence_fake fence_store ubx_nmea demo

OBJ = \
	build/protocol.o build/shape.o build/geofence.o build/cue.o \
	build/gnss_fake.o build/gnss_ubx.o build/fence_store.o \
	build/gossip.o build/power.o build/app.o \
	build/monocypher.o build/monocypher-ed25519.o build/store_ram.o

.PHONY: test deps test-lora clean
.SECONDARY:

test: deps $(TESTS:%=build/test_%) test-lora
	@for t in $(TESTS); do ./build/test_$$t || exit 1; done

deps:
	@if [ ! -f $(LORA)/include/opencollar/fence_node.h ]; then \
	  echo "Fetching $(PROTO_REF) firmware/lora + firmware/sim into $(DEPS)"; \
	  mkdir -p $(DEPS); \
	  git -C $(REPO) archive $(PROTO_REF) firmware/lora firmware/sim | tar -x -C $(DEPS); \
	fi

build/protocol.o: $(SRC)/protocol.c | build
	$(CC) $(CFLAGS) -c -o $@ $<
build/shape.o: $(SRC)/shape.c | build
	$(CC) $(CFLAGS) -c -o $@ $<
build/geofence.o: $(SRC)/geofence.c | build
	$(CC) $(CFLAGS) -c -o $@ $<
build/cue.o: $(SRC)/cue.c | build
	$(CC) $(CFLAGS) -c -o $@ $<
build/gnss_fake.o: $(STARLING)/src/gnss_fake.c | build
	$(CC) $(CFLAGS) -c -o $@ $<
build/gnss_ubx.o: $(STARLING)/src/gnss_ubx.c | build
	$(CC) $(CFLAGS) -c -o $@ $<
build/fence_store.o: $(STARLING)/src/fence_store.c | build
	$(CC) $(CFLAGS) -c -o $@ $<
build/gossip.o: $(STARLING)/src/gossip.c | build
	$(CC) $(CFLAGS) -c -o $@ $<
build/power.o: $(STARLING)/src/power.c | build
	$(CC) $(CFLAGS) -c -o $@ $<
build/app.o: $(STARLING)/src/app.c | build
	$(CC) $(CFLAGS) -c -o $@ $<
build/monocypher.o: $(MONO)/monocypher.c | build
	$(CC) $(CFLAGS) -c -o $@ $<
build/monocypher-ed25519.o: $(MONO)/monocypher-ed25519.c | build
	$(CC) $(CFLAGS) -c -o $@ $<
build/store_ram.o: $(HOST_RAM)/store_ram.c | build
	$(CC) $(CFLAGS) -c -o $@ $<

build/test_%: test_%.c $(OBJ) | build
	$(CC) $(CFLAGS) -o $@ $< $(OBJ) -lm

# --- PR #6-linked gossip high-water test ---------------------------------
LORA_CFLAGS = -std=c11 -Wall -Wextra -Werror -O1 -g -ffp-contract=off \
	-D_POSIX_C_SOURCE=200809L -DSTARLING_HAS_LORA=1 \
	$(BASE_INC) -I$(LORA)/include -I$(LORA)/src -I$(LORA)/tests -I$(SIM)/include

build/lora_fence_node.o: $(LORA)/src/fence_node.c deps | build
	$(CC) $(LORA_CFLAGS) -c -o $@ $<
build/lora_fence_manifest.o: $(LORA)/src/fence_manifest.c deps | build
	$(CC) $(LORA_CFLAGS) -c -o $@ $<
build/lora_fence_wire.o: $(LORA)/src/fence_wire.c deps | build
	$(CC) $(LORA_CFLAGS) -c -o $@ $<
build/lora_fence_hash.o: $(LORA)/src/fence_hash.c deps | build
	$(CC) $(LORA_CFLAGS) -c -o $@ $<
build/lora_fence_build.o: $(LORA)/src/fence_build.c deps | build
	$(CC) $(LORA_CFLAGS) -c -o $@ $<
build/sim_radio.o: $(SIM)/src/sim_radio.c deps | build
	$(CC) $(LORA_CFLAGS) -c -o $@ $<
build/gossip_lora.o: $(STARLING)/src/gossip.c deps | build
	$(CC) $(LORA_CFLAGS) -c -o $@ $<
build/app_lora.o: $(STARLING)/src/app.c deps | build
	$(CC) $(LORA_CFLAGS) -c -o $@ $<
build/fence_store_lora.o: $(STARLING)/src/fence_store.c deps | build
	$(CC) $(LORA_CFLAGS) -c -o $@ $<

test-lora: deps build/test_gossip_hwm
	./build/test_gossip_hwm

build/test_gossip_hwm: test_gossip_hwm.c deps \
		build/protocol.o build/shape.o build/geofence.o build/cue.o \
		build/gnss_fake.o build/gnss_ubx.o build/fence_store_lora.o \
		build/gossip_lora.o build/power.o build/app_lora.o \
		build/monocypher.o build/monocypher-ed25519.o build/store_ram.o \
		build/lora_fence_node.o build/lora_fence_manifest.o \
		build/lora_fence_wire.o build/lora_fence_hash.o build/lora_fence_build.o \
		build/sim_radio.o | build
	$(CC) $(LORA_CFLAGS) -o $@ test_gossip_hwm.c \
		build/protocol.o build/shape.o build/geofence.o build/cue.o \
		build/gnss_fake.o build/gnss_ubx.o build/fence_store_lora.o \
		build/gossip_lora.o build/power.o build/app_lora.o \
		build/monocypher.o build/monocypher-ed25519.o build/store_ram.o \
		build/lora_fence_node.o build/lora_fence_manifest.o \
		build/lora_fence_wire.o build/lora_fence_hash.o build/lora_fence_build.o \
		build/sim_radio.o -lm

build:
	mkdir -p build

clean:
	rm -rf build
